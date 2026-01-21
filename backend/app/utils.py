import secrets
import string
from typing import Optional


def generate_slug(length: int = 7) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_verification_token() -> str:
    # Placeholder - token generation is done in auth module using JWT
    return secrets.token_urlsafe(32)
