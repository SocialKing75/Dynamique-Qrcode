import sys
import os
from fastapi.testclient import TestClient

# ensure project root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.db import Base, engine
Base.metadata.create_all(bind=engine)

from backend.app.main import app
client = TestClient(app)


def test_dashboard_page_loads():
    # without auth should redirect to login
    r = client.get('/dashboard', allow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers.get('location') == '/admin/login'


def test_dashboard_after_login(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'pw')
    r = client.post('/admin/login', data={'password': 'pw'}, allow_redirects=False)
    assert r.status_code in (302, 307)
    client.cookies.set('admin_token', r.cookies['admin_token'])
    r2 = client.get('/dashboard')
    assert r2.status_code == 200
    assert 'QRVerse Pro' in r2.text or 'Dashboard' in r2.text
