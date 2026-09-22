"""Course and member routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import CourseCreate, CourseJoin, CourseOut, CourseStatsOut, MemberOut
from app.services import (
    course_detail,
    course_stats,
    create_course,
    join_course,
    list_courses,
    list_members,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=201)
def create(
    payload: CourseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return create_course(db, user.id, payload.name)


@router.get("", response_model=list[CourseOut])
def list_all(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    return list_courses(db, user.id)


@router.post("/join", response_model=CourseOut)
def join(
    payload: CourseJoin,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return join_course(db, user.id, payload.invite_code)


@router.get("/{course_id}", response_model=CourseOut)
def detail(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return course_detail(db, course_id, user.id)


@router.get("/{course_id}/members", response_model=list[MemberOut])
def members(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_members(db, course_id, user.id)


@router.get("/{course_id}/stats", response_model=CourseStatsOut)
def stats(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return course_stats(db, course_id, user.id)
