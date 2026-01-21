import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env file
load_dotenv()

Base = declarative_base()

# Lazy initialization - avoid crash at import time
_engine = None
_SessionLocal = None
_tables_initialized = False


def get_engine():
    """Get or create the SQLAlchemy engine (lazy initialization)."""
    global _engine
    if _engine is not None:
        return _engine
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    if not DATABASE_URL:
        if os.getenv("VERCEL"):
            # On Vercel, PostgreSQL is required
            raise ValueError("DATABASE_URL is missing on Vercel. Please set it in the Vercel project settings.")
        # For local development, use SQLite
        DATABASE_URL = "sqlite:///./dev.db"
    
    # Standardize Postgres URL if needed (Supabase/Vercel often use postgres://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # SQLite needs special config
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    
    _engine = create_engine(DATABASE_URL, connect_args=connect_args)
    return _engine


def get_session_local():
    """Get or create the SessionLocal factory (lazy initialization)."""
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal
    
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def ensure_tables():
    """Ensure database tables exist. Safe to call multiple times."""
    global _tables_initialized
    if not _tables_initialized:
        Base.metadata.create_all(bind=get_engine())
        _tables_initialized = True


def get_db():
    """Dependency to provide a DB session."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# For backwards compatibility with imports like "from .db import engine"
# These are now properties that trigger lazy initialization
@property
def engine():
    return get_engine()

