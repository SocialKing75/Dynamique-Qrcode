import sys
import os
from fastapi.testclient import TestClient

# ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.db import Base, engine

from backend.app.main import app

client = TestClient(app)


def test_dynamic_qr_update_flow():
    # create a dynamic QR
    payload = {"content": "https://original.example", "is_dynamic": True}
    r = client.post('/api/qrcodes/', json=payload)
    assert r.status_code == 200
    data = r.json()
    qid = data['id']
    slug = data['slug']

    # ensure redirect is original
    r2 = client.get(f"/q/{slug}", allow_redirects=False)
    assert r2.status_code in (302, 307)
    assert r2.headers['location'] == 'https://original.example'

    # update the QR content
    up = {"content": "https://updated.example"}
    r3 = client.patch(f"/api/qrcodes/{qid}", json=up)
    assert r3.status_code == 200

    # ensure redirect now uses updated content
    r4 = client.get(f"/q/{slug}", allow_redirects=False)
    assert r4.status_code in (302, 307)
    assert r4.headers['location'] == 'https://updated.example'

    # cleanup not needed (uses sqlite dev.db)
