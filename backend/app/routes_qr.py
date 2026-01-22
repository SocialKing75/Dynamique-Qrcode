from fastapi import APIRouter, HTTPException, Query, Response, Request
from typing import Optional
from bson import ObjectId
from . import schemas, models
from .auth import require_admin_from_request
from .utils import generate_slug
from segno import make as make_qr
from datetime import datetime, timedelta
from io import BytesIO
from starlette.responses import StreamingResponse
import re

router = APIRouter(prefix="/api/qrcodes", tags=["qrcodes"])


@router.post("/")
async def create_qr(data: schemas.QRCreate):
    slug = generate_slug(7)
    while await models.QRCode.find_one(models.QRCode.slug == slug):
        slug = generate_slug(7)
    q = models.QRCode(
        slug=slug,
        title=data.title or "",
        content=data.content,
        is_dynamic=data.is_dynamic,
        options=data.options or {}
    )
    await q.insert()
    return {"id": str(q.id), "slug": q.slug}


@router.get("/")
async def list_qrcodes(
    dynamic: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_desc"),
    request: Request = None
):
    """List QR codes with pagination, search and sorting."""
    # If caller requests dynamic filter, require admin
    if dynamic is True:
        if request is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        require_admin_from_request(request)

    # Build query filter
    query_filter = {}

    if dynamic is not None:
        query_filter["is_dynamic"] = dynamic

    if search:
        pattern = re.compile(f".*{re.escape(search)}.*", re.IGNORECASE)
        query_filter["$or"] = [
            {"title": {"$regex": pattern}},
            {"slug": {"$regex": pattern}},
            {"content": {"$regex": pattern}}
        ]

    # Get total count
    total = await models.QRCode.find(query_filter).count()

    # Sorting
    sort_field = "created_at"
    sort_dir = -1  # descending
    if sort == "created_asc":
        sort_dir = 1
    elif sort == "title_asc":
        sort_field = "title"
        sort_dir = 1
    elif sort == "title_desc":
        sort_field = "title"
        sort_dir = -1

    # Pagination
    offset = (page - 1) * limit
    results = await models.QRCode.find(query_filter).sort(
        [(sort_field, sort_dir)]
    ).skip(offset).limit(limit).to_list()

    # Get click counts via aggregation
    click_counts = {}
    if results:
        ids = [r.id for r in results]
        pipeline = [
            {"$match": {"qrcode_id": {"$in": ids}}},
            {"$group": {"_id": "$qrcode_id", "count": {"$sum": 1}}}
        ]
        counts = await models.Click.aggregate(pipeline).to_list()
        click_counts = {c["_id"]: c["count"] for c in counts}

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "items": [
            {
                "id": str(r.id),
                "slug": r.slug,
                "title": r.title,
                "content": r.content,
                "is_dynamic": r.is_dynamic,
                "options": r.options,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "click_count": click_counts.get(r.id, 0)
            }
            for r in results
        ]
    }


@router.patch("/{qrcode_id}")
async def update_qr(qrcode_id: str, data: schemas.QRUpdate, request: Request):
    if not ObjectId.is_valid(qrcode_id):
        raise HTTPException(status_code=400, detail="Invalid QRCode ID")

    q = await models.QRCode.get(qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    if not q.is_dynamic:
        raise HTTPException(status_code=403, detail="QRCode is not dynamic")

    if request is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    require_admin_from_request(request)

    if data.title is not None:
        q.title = data.title
    if data.content is not None:
        q.content = data.content
    if data.is_dynamic is not None:
        q.is_dynamic = data.is_dynamic
    if data.options is not None:
        q.options = data.options

    q.updated_at = datetime.utcnow()
    await q.save()
    return {
        "id": str(q.id),
        "slug": q.slug,
        "title": q.title,
        "content": q.content,
        "is_dynamic": q.is_dynamic,
        "options": q.options,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None
    }


@router.get('/admin/stats')
async def admin_stats(request: Request):
    require_admin_from_request(request)
    total_qr = await models.QRCode.find().count()
    dynamic_qr = await models.QRCode.find(models.QRCode.is_dynamic == True).count()
    total_clicks = await models.Click.find().count()
    return {"total_qr": total_qr, "dynamic_qr": dynamic_qr, "total_clicks": total_clicks}


@router.get('/{qrcode_id}/analytics')
async def qrcode_analytics(qrcode_id: str, days: int = Query(30, ge=1, le=365)):
    """Return timeseries of clicks per day for the given qrcode."""
    if not ObjectId.is_valid(qrcode_id):
        raise HTTPException(status_code=400, detail="Invalid QRCode ID")

    q = await models.QRCode.get(qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    cutoff = datetime.utcnow() - timedelta(days=days)

    pipeline = [
        {"$match": {
            "qrcode_id": q.id,
            "timestamp": {"$gte": cutoff}
        }},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]

    rows = await models.Click.aggregate(pipeline).to_list()
    counts = {r["_id"]: r["count"] for r in rows}

    # Build timeseries for all days
    days_list = [(datetime.utcnow() - timedelta(days=i)).date() for i in range(days-1, -1, -1)]
    series = [counts.get(d.isoformat(), 0) for d in days_list]
    labels = [d.isoformat() for d in days_list]

    return {"labels": labels, "series": series}


@router.get('/{qrcode_id}/clicks')
async def qrcode_clicks(
    qrcode_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100)
):
    """Return detailed click history for a QR code with pagination."""
    if not ObjectId.is_valid(qrcode_id):
        raise HTTPException(status_code=400, detail="Invalid QRCode ID")

    q = await models.QRCode.get(qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    # Get total count
    total = await models.Click.find(models.Click.qrcode_id == q.id).count()

    # Get paginated clicks
    offset = (page - 1) * limit
    clicks = await models.Click.find(
        models.Click.qrcode_id == q.id
    ).sort([("timestamp", -1)]).skip(offset).limit(limit).to_list()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "clicks": [
            {
                "id": str(c.id),
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "ip": c.ip,
                "user_agent": c.user_agent,
                "country": c.country
            }
            for c in clicks
        ]
    }


@router.get("/{qrcode_id}/image")
async def get_image(qrcode_id: str, request: Request, format: str = Query("png"), size: int = Query(300)):
    if not ObjectId.is_valid(qrcode_id):
        raise HTTPException(status_code=400, detail="Invalid QRCode ID")

    q = await models.QRCode.get(qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    # For dynamic QR codes, encode the redirect URL; for static, encode the content directly
    if q.is_dynamic:
        base_url = str(request.base_url).rstrip('/')
        qr_url = f"{base_url}/q/{q.slug}"
    else:
        qr_url = q.content

    qr = make_qr(qr_url)
    if format == "svg":
        svg_io = BytesIO()
        qr.save(svg_io, kind="svg")
        svg_io.seek(0)
        return Response(content=svg_io.read(), media_type="image/svg+xml")
    else:
        png_io = BytesIO()
        try:
            modules_x, modules_y = qr.symbol_size()
            scale = max(1, int(size // max(modules_x, modules_y)))
        except Exception:
            scale = 1
        qr.save(png_io, kind="png", scale=scale)
        png_io.seek(0)
        return StreamingResponse(png_io, media_type="image/png")


@router.get("/slug/{slug}")
async def get_qr_by_slug(slug: str):
    q = await models.QRCode.find_one(models.QRCode.slug == slug)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")
    return {
        "id": str(q.id),
        "slug": q.slug,
        "title": q.title,
        "content": q.content,
        "is_dynamic": q.is_dynamic,
        "options": q.options,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None
    }


@router.delete("/{qrcode_id}")
async def delete_qr(qrcode_id: str, request: Request):
    """Delete a single QR code by ID. Requires admin authentication."""
    require_admin_from_request(request)

    if not ObjectId.is_valid(qrcode_id):
        raise HTTPException(status_code=400, detail="Invalid QRCode ID")

    q = await models.QRCode.get(qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    # Delete associated clicks first
    await models.Click.find(models.Click.qrcode_id == q.id).delete()
    await q.delete()

    return {"message": "QR code deleted successfully"}


@router.delete("/")
async def delete_all_qrcodes(request: Request):
    """Delete all QR codes. Requires admin authentication."""
    require_admin_from_request(request)

    # Delete all clicks first
    await models.Click.delete_all()
    # Delete all QR codes
    result = await models.QRCode.delete_all()

    return {"message": f"All QR codes deleted successfully"}
