import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

# ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.db import Base, engine

from backend.app.main import app
client = TestClient(app)


def test_admin_login_and_protected_routes(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'secretpw')

    # ensure protected endpoints require auth
    r = client.get('/api/qrcodes?dynamic=true')
    assert r.status_code == 401 or r.status_code == 403

    # create a dynamic QR (public)
    r2 = client.post('/api/qrcodes/', json={'content': 'https://public.example', 'is_dynamic': True})
    assert r2.status_code == 200
    data = r2.json()
    qid = data['id']

    # try to patch without auth
    r3 = client.patch(f'/api/qrcodes/{qid}', json={'content': 'https://bad.example'})
    assert r3.status_code == 401 or r3.status_code == 403

    # login as admin (form submit)
    r4 = client.post('/admin/login', data={'password': 'secretpw'}, allow_redirects=False)
    assert r4.status_code in (302, 307)
    assert 'admin_token' in r4.cookies

    # follow redirect and access dashboard
    client.cookies.set('admin_token', r4.cookies['admin_token'])
    r5 = client.get('/dashboard')
    assert r5.status_code == 200

    # call stats endpoint
    r6 = client.get('/api/admin/stats')
    assert r6.status_code == 200
    assert 'total_qr' in r6.json()

    # patch should succeed now
    r7 = client.patch(f'/api/qrcodes/{qid}', json={'content': 'https://updated.example'})
    assert r7.status_code == 200