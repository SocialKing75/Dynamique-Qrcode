from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
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
    try:
        await init_db()
        print("✓ MongoDB initialized successfully")
    except Exception as e:
        print(f"✗ MongoDB initialization error: {e}")
        raise
    yield
    # Shutdown: Close connection
    await close_db()


app = FastAPI(title="QRGen API", lifespan=lifespan)

# Configure templates (static files are handled by vercel.json rewrites)
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
print(f"Templates directory: {templates_dir}")
print(f"Templates directory exists: {os.path.exists(templates_dir)}")
templates = Jinja2Templates(directory=templates_dir)

app.include_router(auth_router)
app.include_router(qr_router)
app.include_router(redirect_router)
app.include_router(admin_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for debugging."""
    import sys
    return {
        "status": "ok",
        "python_version": sys.version,
        "templates_dir": templates_dir,
        "templates_exists": os.path.exists(templates_dir),
        "pwd": os.getcwd(),
        "env_vars": {
            "MONGODB_URL": "configured" if os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI") else "missing",
            "MONGODB_DB_NAME": os.getenv("MONGODB_DB_NAME", "not set")
        }
    }


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


@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files (CSS, JS, images)."""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    file_location = os.path.join(static_dir, file_path)

    if not os.path.exists(file_location):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_location)
