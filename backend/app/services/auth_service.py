"""Authentication use cases."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import TokenResponse


def register_user(db: Session, email: str, password: str, display_name: str) -> TokenResponse:
    normalized_email = email.strip().lower()
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("EMAIL_EXISTS", "该邮箱已经注册。", 409) from exc
    db.refresh(user)
    return _token_response(user)


def login_user(db: Session, email: str, password: str) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "邮箱或密码错误。", 401)
    return _token_response(user)


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.token_expire_seconds,
        user=user,
    )
