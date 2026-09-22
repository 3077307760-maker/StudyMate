"""Data access checks shared by all services and routers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Conversation, Course, CourseMember, Document, Quiz


def require_member(db: Session, course_id: str, user_id: str) -> CourseMember:
    member = db.get(CourseMember, (course_id, user_id))
    if member:
        return member
    if not db.get(Course, course_id):
        raise AppError("NOT_FOUND", "课程不存在。", 404)
    raise AppError("FORBIDDEN", "你不是该课程成员。", 403)


def require_owner(db: Session, course_id: str, user_id: str) -> CourseMember:
    member = require_member(db, course_id, user_id)
    if member.role != "owner":
        raise AppError("FORBIDDEN", "只有课程创建者可以执行此操作。", 403)
    return member


def get_document_for_member(db: Session, document_id: str, user_id: str) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise AppError("NOT_FOUND", "文档不存在。", 404)
    require_member(db, document.course_id, user_id)
    return document


def get_conversation_for_owner(db: Session, conversation_id: str, user_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise AppError("NOT_FOUND", "会话不存在。", 404)
    if conversation.user_id != user_id:
        raise AppError("FORBIDDEN", "不能查看他人的会话。", 403)
    require_member(db, conversation.course_id, user_id)
    return conversation


def get_quiz_for_member(db: Session, quiz_id: str, user_id: str) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if not quiz:
        raise AppError("NOT_FOUND", "练习不存在。", 404)
    require_member(db, quiz.course_id, user_id)
    return quiz


def get_courses_for_user(db: Session, user_id: str) -> list[tuple[Course, str]]:
    rows = db.execute(
        select(Course, CourseMember.role)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .where(CourseMember.user_id == user_id)
        .order_by(Course.updated_at.desc())
    ).all()
    return [(row[0], row[1]) for row in rows]
