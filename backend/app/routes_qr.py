from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from . import schemas, models
from .db import get_db, ensure_tables
from .auth import require_admin_from_request
from fastapi import Depends
from .utils import generate_slug
from segno import make as make_qr
from datetime import datetime, timedelta
from io import BytesIO
from starlette.responses import RedirectResponse, StreamingResponse
import json

router = APIRouter(prefix="/api/qrcodes", tags=["qrcodes"])


@router.post("/")
def create_qr(data: schemas.QRCreate, db: Session = Depends(get_db)):
    ensure_tables()  # Ensure tables exist on first request
    slug = generate_slug(7)
    while db.query(models.QRCode).filter(models.QRCode.slug == slug).first():
        slug = generate_slug(7)
    q = models.QRCode(slug=slug, title=data.title or "", content=data.content, is_dynamic=data.is_dynamic, options=data.options)
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "slug": q.slug}


@router.get("/")
def list_qrcodes(
    dynamic: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_desc"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """List QR codes with pagination, search and sorting.

    Query params:
    - dynamic: filter by dynamic status
    - search: search in title and slug
    - page: page number (default 1)
    - limit: items per page (default 20, max 100)
    - sort: created_desc (default), created_asc, title_asc, title_desc, clicks_desc
    """
    # If caller requests dynamic filter, require admin
    if dynamic is True:
        if request is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        require_admin_from_request(request)

    q = db.query(models.QRCode)

    # Filter by dynamic
    if dynamic is True:
        q = q.filter(models.QRCode.is_dynamic.is_(True))
    elif dynamic is False:
        q = q.filter(models.QRCode.is_dynamic.is_(False))

    # Search filter
    if search:
        search_term = f"%{search}%"
        q = q.filter(
            (models.QRCode.title.ilike(search_term)) |
            (models.QRCode.slug.ilike(search_term)) |
            (models.QRCode.content.ilike(search_term))
        )

    # Get total count before pagination
    total = q.count()

    # Sorting
    if sort == "created_asc":
        q = q.order_by(models.QRCode.created_at.asc())
    elif sort == "title_asc":
        q = q.order_by(models.QRCode.title.asc())
    elif sort == "title_desc":
        q = q.order_by(models.QRCode.title.desc())
    else:  # created_desc (default)
        q = q.order_by(models.QRCode.created_at.desc())

    # Pagination
    offset = (page - 1) * limit
    results = q.offset(offset).limit(limit).all()

    # Add click count to each result
    from sqlalchemy import func
    click_counts = {}
    if results:
        ids = [r.id for r in results]
        counts = db.query(
            models.Click.qrcode_id,
            func.count(models.Click.id).label('count')
        ).filter(models.Click.qrcode_id.in_(ids)).group_by(models.Click.qrcode_id).all()
        click_counts = {c.qrcode_id: c.count for c in counts}

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "items": [
            {
                "id": r.id,
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
def update_qr(qrcode_id: int, data: schemas.QRUpdate, request: Request, db: Session = Depends(get_db)):
    q = db.get(models.QRCode, qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")
    # Only allow updating content/title/options when QR is dynamic
    if not q.is_dynamic:
        raise HTTPException(status_code=403, detail="QRCode is not dynamic")
    # Require admin to update dynamic QRs
    # Note: dynamic QR content used to be updateable without auth; change to require admin
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
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.get('/admin/stats')
def admin_stats(request: Request, db: Session = Depends(get_db)):
    # admin-only stats endpoint
    require_admin_from_request(request)
    total_qr = db.query(models.QRCode).count()
    dynamic_qr = db.query(models.QRCode).filter(models.QRCode.is_dynamic.is_(True)).count()
    total_clicks = db.query(models.Click).count()
    return {"total_qr": total_qr, "dynamic_qr": dynamic_qr, "total_clicks": total_clicks}


@router.get('/{qrcode_id}/analytics')
def qrcode_analytics(qrcode_id: int, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    """Return timeseries of clicks per day for the given qrcode for the past `days` days."""
    # ensure QR exists
    q = db.get(models.QRCode, qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")
    # aggregate clicks by date
    from sqlalchemy import func, cast, Date
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = db.query(cast(models.Click.timestamp, Date).label('day'), func.count(models.Click.id).label('count'))\
        .filter(models.Click.qrcode_id == qrcode_id, models.Click.timestamp >= cutoff)\
        .group_by('day')\
        .order_by('day')\
        .all()
    # build timeseries for all days (fill zeros)
    days_list = [(datetime.utcnow() - timedelta(days=i)).date() for i in range(days-1, -1, -1)]
    counts = {r.day: r.count for r in rows}
    series = [counts.get(d, 0) for d in days_list]
    labels = [d.isoformat() for d in days_list]
    return {"labels": labels, "series": series}


@router.get('/{qrcode_id}/clicks')
def qrcode_clicks(
    qrcode_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Return detailed click history for a QR code with pagination."""
    q = db.get(models.QRCode, qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")

    # Get total count
    total = db.query(models.Click).filter(models.Click.qrcode_id == qrcode_id).count()

    # Get paginated clicks
    offset = (page - 1) * limit
    clicks = db.query(models.Click)\
        .filter(models.Click.qrcode_id == qrcode_id)\
        .order_by(models.Click.timestamp.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "clicks": [
            {
                "id": c.id,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                "ip": c.ip,
                "user_agent": c.user_agent,
                "country": c.country
            }
            for c in clicks
        ]
    }


@router.get("/{qrcode_id}/image")
def get_image(qrcode_id: int, request: Request, format: str = Query("png"), size: int = Query(300), db: Session = Depends(get_db)):
    # Prefer Session.get over the deprecated Query.get
    q = db.get(models.QRCode, qrcode_id)
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
        # Compute a reasonable scale so the generated PNG is roughly `size` pixels
        try:
            modules_x, modules_y = qr.symbol_size()
            # scale = pixels per module
            scale = max(1, int(size // max(modules_x, modules_y)))
        except Exception:
            scale = 1
        qr.save(png_io, kind="png", scale=scale)
        png_io.seek(0)
        return StreamingResponse(png_io, media_type="image/png")


@router.get("/slug/{slug}")
def get_qr_by_slug(slug: str, db: Session = Depends(get_db)):
    q = db.query(models.QRCode).filter(models.QRCode.slug == slug).first()
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")
    return q


@router.delete("/{qrcode_id}")
def delete_qr(qrcode_id: int, request: Request, db: Session = Depends(get_db)):
    """Delete a single QR code by ID. Requires admin authentication."""
    require_admin_from_request(request)
    q = db.get(models.QRCode, qrcode_id)
    if not q:
        raise HTTPException(status_code=404, detail="QRCode not found")
    # Delete associated clicks first
    db.query(models.Click).filter(models.Click.qrcode_id == qrcode_id).delete()
    db.delete(q)
    db.commit()
    return {"message": "QR code deleted successfully"}


@router.delete("/")
def delete_all_qrcodes(request: Request, db: Session = Depends(get_db)):
    """Delete all QR codes. Requires admin authentication."""
    require_admin_from_request(request)
    # Delete all clicks first
    db.query(models.Click).delete()
    # Delete all QR codes
    count = db.query(models.QRCode).delete()
    db.commit()
    return {"message": f"{count} QR codes deleted successfully"}


# Redirection route (not under /api)
