"""Password hashing and JWT helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.token_expire_seconds),
        "type": "access",
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    subject = payload.get("sub")
    if not subject or payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token payload")
    return str(subject)
