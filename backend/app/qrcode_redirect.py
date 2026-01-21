from fastapi import APIRouter, Depends, Request
from starlette.responses import RedirectResponse
from sqlalchemy.orm import Session
from .db import get_db
from . import models

router = APIRouter()


@router.get("/q/{slug}")
def redirect_slug(slug: str, request: Request, db: Session = Depends(get_db)):
    q = db.query(models.QRCode).filter(models.QRCode.slug == slug).first()
    if not q:
        return RedirectResponse(url="/", status_code=302)
    # record click
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    click = models.Click(qrcode_id=q.id, ip=ip, user_agent=ua)
    db.add(click)
    db.commit()
    return RedirectResponse(url=q.content)
