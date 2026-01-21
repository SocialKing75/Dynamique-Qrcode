from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Any, Dict
from datetime import datetime
from urllib.parse import urlparse

# Blocked URL schemes that could be used for phishing or attacks
BLOCKED_SCHEMES = {'javascript', 'data', 'vbscript', 'file'}

# Blocked domains commonly used for phishing (can be extended)
BLOCKED_DOMAINS = set()


def validate_url_safety(url: str) -> str:
    """Validate that URL is safe (no javascript:, data:, etc.)"""
    if not url:
        return url

    url_lower = url.lower().strip()

    # Check for blocked schemes
    for scheme in BLOCKED_SCHEMES:
        if url_lower.startswith(f"{scheme}:"):
            raise ValueError(f"URL scheme '{scheme}:' is not allowed")

    # Parse URL to validate structure
    try:
        parsed = urlparse(url)
        # Only allow http, https, mailto, tel, and empty (relative) schemes
        allowed_schemes = {'http', 'https', 'mailto', 'tel', ''}
        if parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed. Use http or https.")

        # Check for blocked domains
        if parsed.netloc.lower() in BLOCKED_DOMAINS:
            raise ValueError("This domain is not allowed")

    except ValueError:
        raise
    except Exception:
        # If URL parsing fails, it might still be valid content (like plain text for QR)
        pass

    return url


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_verified: bool

    class Config:
        orm_mode = True


class QRCreate(BaseModel):
    title: Optional[str]
    content: str
    is_dynamic: Optional[bool] = False
    # Use default_factory to avoid mutable default shared between instances
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('content')
    def validate_content(cls, v):
        return validate_url_safety(v)


class QRUpdate(BaseModel):
    title: Optional[str]
    content: Optional[str]
    is_dynamic: Optional[bool]
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('content')
    def validate_content(cls, v):
        if v is not None:
            return validate_url_safety(v)
        return v


class QROut(BaseModel):
    id: int
    slug: str
    title: Optional[str]
    content: str
    is_dynamic: bool
    options: Dict[str, Any]
    created_at: datetime

    class Config:
        orm_mode = True
