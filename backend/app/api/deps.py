"""Authentication dependencies shared by routers."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("AUTH_REQUIRED", "请先登录。", 401)
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AppError("AUTH_REQUIRED", "登录状态已失效，请重新登录。", 401) from exc
    user = db.get(User, user_id)
    if not user:
        raise AppError("AUTH_REQUIRED", "用户不存在，请重新登录。", 401)
    return user
