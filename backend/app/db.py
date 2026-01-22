import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

load_dotenv()

_client = None
_db = None


async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    global _client, _db

    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("MONGODB_DB_NAME", "qrgen")

    _client = AsyncIOMotorClient(MONGODB_URL)
    _db = _client[DB_NAME]

    # Import models here to avoid circular imports
    from .models import User, QRCode, Click

    await init_beanie(
        database=_db,
        document_models=[User, QRCode, Click]
    )


async def close_db():
    """Close MongoDB connection."""
    global _client
    if _client:
        _client.close()


def get_db():
    """Return the database instance for direct queries if needed."""
    return _db
