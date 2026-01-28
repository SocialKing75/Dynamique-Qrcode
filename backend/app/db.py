import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

load_dotenv()

_client = None
_db = None
_initialized = False


def get_mongodb_url():
    """Get MongoDB URL from environment variables."""
    # Support both MONGODB_URL and MONGODB_URI (Atlas standard)
    url = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
    if not url:
        url = "mongodb://localhost:27017"
    return url


async def init_db():
    """Initialize MongoDB connection and Beanie ODM."""
    global _client, _db, _initialized

    if _initialized:
        return

    MONGODB_URL = get_mongodb_url()
    DB_NAME = os.getenv("MONGODB_DB_NAME", "qrgen")

    # Configure client with serverless-friendly timeouts
    _client = AsyncIOMotorClient(
        MONGODB_URL,
        serverSelectionTimeoutMS=5000,  # 5s timeout for server selection
        connectTimeoutMS=5000,           # 5s timeout for connection
        socketTimeoutMS=10000,           # 10s timeout for operations
        maxPoolSize=10,                  # Limit connections for serverless
        minPoolSize=0,                   # Allow pool to shrink
    )
    _db = _client[DB_NAME]

    # Import models here to avoid circular imports
    from .models import User, QRCode, Click, ProcessedFile

    await init_beanie(
        database=_db,
        document_models=[User, QRCode, Click, ProcessedFile]
    )
    _initialized = True


async def close_db():
    """Close MongoDB connection."""
    global _client, _initialized
    if _client:
        _client.close()
        _initialized = False


def get_db():
    """Return the database instance for direct queries if needed."""
    return _db
