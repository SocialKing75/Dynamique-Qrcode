from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
import os
from datetime import timedelta
from . import auth, models

router = APIRouter()


@router.get("/admin/login")
async def login_form(request: Request):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.post("/admin/login")
async def login(request: Request, password: str = Form(None)):
    if password is None:
        try:
            data = await request.json()
            password = data.get('password')
        except Exception:
            password = None
    admin_pw = os.getenv('ADMIN_PASSWORD')
    if not admin_pw:
        raise HTTPException(status_code=403, detail="Admin login not configured")
    if password != admin_pw:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth.create_access_token({"admin": True}, expires_delta=timedelta(days=1))
    resp = RedirectResponse(url='/admin', status_code=302)
    resp.set_cookie('admin_token', token, httponly=True, samesite='lax')
    return resp


@router.post('/admin/logout')
async def logout():
    resp = RedirectResponse(url='/', status_code=302)
    resp.delete_cookie('admin_token')
    return resp


@router.get('/api/admin/stats')
async def api_admin_stats(request: Request):
    """Compatibility endpoint for admin stats at /api/admin/stats"""
    auth.require_admin_from_request(request)
    total_qr = await models.QRCode.find().count()
    dynamic_qr = await models.QRCode.find(models.QRCode.is_dynamic == True).count()
    total_clicks = await models.Click.find().count()
    return {"total_qr": total_qr, "dynamic_qr": dynamic_qr, "total_clicks": total_clicks}
