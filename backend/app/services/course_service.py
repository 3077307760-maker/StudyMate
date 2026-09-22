"""Course and membership use cases."""

import secrets
import string
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    Conversation,
    Course,
    CourseMember,
    Document,
    Quiz,
    User,
    WrongItem,
)
from app.repositories import get_courses_for_user, require_owner

ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"


def create_course(db: Session, user_id: str, name: str) -> dict[str, object]:
    for _ in range(20):
        course = Course(name=name.strip(), invite_code=_new_invite_code(), owner_id=user_id)
        db.add(course)
        db.flush()
        db.add(CourseMember(course_id=course.id, user_id=user_id, role="owner"))
        try:
            db.commit()
            db.refresh(course)
            return _course_payload(course, "owner")
        except IntegrityError:
            db.rollback()
            continue
    raise AppError("INVITE_CODE_EXHAUSTED", "暂时无法生成邀请码，请重试。", 503)


def join_course(db: Session, user_id: str, invite_code: str) -> dict[str, object]:
    course = db.scalar(select(Course).where(Course.invite_code == invite_code.upper()))
    if not course:
        raise AppError("INVALID_INVITE_CODE", "邀请码无效。", 404)
    member = db.get(CourseMember, (course.id, user_id))
    if not member:
        db.add(CourseMember(course_id=course.id, user_id=user_id, role="member"))
        db.commit()
    return _course_payload(course, member.role if member else "member")


def list_courses(db: Session, user_id: str) -> list[dict[str, object]]:
    return [_course_payload(course, role) for course, role in get_courses_for_user(db, user_id)]


def course_detail(db: Session, course_id: str, user_id: str) -> dict[str, object]:
    from app.repositories import require_member

    member = require_member(db, course_id, user_id)
    course = db.get(Course, course_id)
    assert course is not None
    return _course_payload(course, member.role)


def list_members(db: Session, course_id: str, user_id: str) -> list[dict[str, object]]:
    from app.repositories import require_member

    require_member(db, course_id, user_id)
    rows = db.execute(
        select(User, CourseMember.role, CourseMember.joined_at)
        .join(CourseMember, CourseMember.user_id == User.id)
        .where(CourseMember.course_id == course_id)
        .order_by(CourseMember.joined_at)
    ).all()
    return [
        {
            "id": row[0].id,
            "display_name": row[0].display_name,
            "email": row[0].email,
            "role": row[1],
            "joined_at": row[2],
        }
        for row in rows
    ]


def course_stats(db: Session, course_id: str, user_id: str) -> dict[str, int]:
    from app.repositories import require_member

    require_member(db, course_id, user_id)

    def count(model: type[object], *criteria: Any) -> int:
        statement = select(func.count()).select_from(model)
        if criteria:
            statement = statement.where(*criteria)
        return int(db.scalar(statement) or 0)

    return {
        "document_count": count(Document, Document.course_id == course_id),
        "ready_document_count": count(
            Document, Document.course_id == course_id, Document.status == "ready"
        ),
        "member_count": count(CourseMember, CourseMember.course_id == course_id),
        "conversation_count": count(Conversation, Conversation.course_id == course_id),
        "quiz_count": count(Quiz, Quiz.course_id == course_id),
        "wrong_item_count": count(
            WrongItem, WrongItem.course_id == course_id, WrongItem.mastered.is_(False)
        ),
    }


def delete_course(db: Session, course_id: str, user_id: str) -> None:
    require_owner(db, course_id, user_id)
    course = db.get(Course, course_id)
    if not course:
        raise AppError("NOT_FOUND", "课程不存在。", 404)
    db.delete(course)
    db.commit()


def _new_invite_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(6))


def _course_payload(course: Course, role: str) -> dict[str, object]:
    return {
        "id": course.id,
        "name": course.name,
        "invite_code": course.invite_code,
        "owner_id": course.owner_id,
        "role": role,
        "created_at": course.created_at,
    }
