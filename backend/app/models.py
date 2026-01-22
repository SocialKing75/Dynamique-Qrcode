from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime


class User(Document):
    email: Indexed(EmailStr, unique=True)
    hashed_password: str
    is_active: bool = False
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"


class QRCode(Document):
    slug: Indexed(str, unique=True)
    title: str = ""
    content: str
    owner_id: Optional[PydanticObjectId] = None
    is_dynamic: bool = False
    options: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "qrcodes"


class Click(Document):
    qrcode_id: PydanticObjectId
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    country: Optional[str] = None

    class Settings:
        name = "clicks"
        indexes = [
            "qrcode_id",
            "timestamp",
        ]
