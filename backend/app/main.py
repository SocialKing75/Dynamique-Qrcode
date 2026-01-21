from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .db import Base, get_engine
from starlette.responses import RedirectResponse
from .routes_auth import router as auth_router
from .routes_qr import router as qr_router
from .qrcode_redirect import router as redirect_router
from .routes_admin import router as admin_router
from .auth import require_admin_from_request
import os
import traceback

app = FastAPI(title="QRGen API")


@app.get("/api/debug")
def debug():
    """Debug endpoint to test database connection."""
    import os
    result = {
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "VERCEL": os.getenv("VERCEL"),
    }
    try:
        engine = get_engine()
        result["engine_url"] = str(engine.url).replace(engine.url.password or "", "***") if engine.url.password else str(engine.url)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        result["db_connection"] = "OK"
    except Exception as e:
        result["db_error"] = str(e)
        result["traceback"] = traceback.format_exc()
    return result

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
def root(request: Request):
    """Serve a simple HTML frontend for creating QR codes and testing redirects."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin")
def admin(request: Request):
    """Admin page to manage dynamic QR codes."""
    try:
        require_admin_from_request(request)
    except Exception:
        return RedirectResponse(url="/admin/login", status_code=302)
    return templates.TemplateResponse("admin.html", {"request": request})

