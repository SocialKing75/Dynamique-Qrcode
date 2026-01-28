from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse
from . import models

router = APIRouter()


@router.get("/q/{slug}")
async def redirect_slug(slug: str, request: Request):
    q = await models.QRCode.find_one(models.QRCode.slug == slug)
    if not q:
        return RedirectResponse(url="/", status_code=302)
    # record click
    import hashlib
    ip_raw = request.client.host if request.client else "unknown"
    # GDPR: Anonymize IP by hashing
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16] # Keep first 16 chars for brevity but anonymity
    
    ua = request.headers.get("user-agent")
    click = models.Click(qrcode_id=q.id, ip=ip_hash, user_agent=ua)
    await click.insert()
    return RedirectResponse(url=q.content)
