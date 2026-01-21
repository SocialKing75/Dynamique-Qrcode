import sys
import os
import pytest

# make sure the repository root is on sys.path for test collection
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use a dedicated test sqlite file for consistency across the TestClient and app imports
import os
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.test.db'))
os.environ.setdefault('DATABASE_URL', f'sqlite:///{test_db_path}')

from backend.app.db import Base, engine
from backend.app import models  # Ensure models are imported so table metadata is registered


@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    # Create tables for tests and drop them at the end
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
