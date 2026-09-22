"""Health endpoint used by Docker and operations."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai import get_vector_index
from app.core.database import get_db
from app.schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database = "unavailable"
    return HealthOut(status="ok", database=database, vector_store=get_vector_index().health())
