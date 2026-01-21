import sys
import os
import pytest

# Ensure repository root is on sys.path so `backend` package is importable when running tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import models, schemas
from backend.app.db import Base, engine, SessionLocal


def setup_module(module):
    # create tables in a temporary sqlite file
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    # drop tables
    Base.metadata.drop_all(bind=engine)


def test_qrcode_options_default_is_dict():
    db = SessionLocal()
    try:
        q = models.QRCode(slug="abc1234", title="t", content="https://example.com")
        db.add(q)
        db.commit()
        db.refresh(q)
        assert isinstance(q.options, dict)
        assert q.options == {}
    finally:
        db.close()


def test_pydantic_qrcreate_options_default():
    qr = schemas.QRCreate(content="https://example.com")
    assert isinstance(qr.options, dict)
    assert qr.options == {}
