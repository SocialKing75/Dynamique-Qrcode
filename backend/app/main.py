from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from starlette.responses import RedirectResponse
from .routes_auth import router as auth_router
from .routes_qr import router as qr_router
from .qrcode_redirect import router as redirect_router
from .routes_admin import router as admin_router
from .auth import require_admin_from_request
from .db import init_db, close_db
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB
    await init_db()
    yield
    # Shutdown: Close connection
    await close_db()


app = FastAPI(title="QRGen API", lifespan=lifespan)

# Mount static files and templates
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(auth_router)
app.include_router(qr_router)
app.include_router(redirect_router)
app.include_router(admin_router)


@app.get("/")
async def root(request: Request):
    """Serve a simple HTML frontend for creating QR codes and testing redirects."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin")
async def admin(request: Request):
    """Admin page to manage dynamic QR codes."""
    try:
        require_admin_from_request(request)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request})
