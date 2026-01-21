import sys
import os
from fastapi.testclient import TestClient

# ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.db import Base, engine

from backend.app.main import app

client = TestClient(app)


def test_root_returns_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "QRGen" in r.text


def test_create_qr_and_redirect_and_image():
    payload = {"content": "https://example.com"}
    r = client.post("/api/qrcodes/", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "slug" in data and "id" in data

    slug = data["slug"]
    # check redirect
    r2 = client.get(f"/q/{slug}", allow_redirects=False)
    assert r2.status_code in (302, 307)
    assert r2.headers.get("location") == "https://example.com"

    # check image endpoint
    r3 = client.get(f"/api/qrcodes/{data['id']}/image?size=200")
    assert r3.status_code == 200
    assert r3.headers["content-type"] in ("image/png", "image/svg+xml")
