"""Authentication and profile routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import LoginRequest, ProfileUpdate, RegisterRequest, TokenResponse, UserOut
from app.services import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return register_user(db, payload.email, payload.password, payload.display_name)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_user(db, payload.email, payload.password)


me_router = APIRouter(tags=["users"])


@me_router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@me_router.patch("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user.display_name = payload.display_name.strip()
    db.commit()
    db.refresh(user)
    return user
