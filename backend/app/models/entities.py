"""SQLAlchemy entities for the StudyMate MVP."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uuid_str() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100))
    invite_code: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    members: Mapped[list[CourseMember]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class CourseMember(Base):
    __tablename__ = "course_members"

    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(10))
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    course: Mapped[Course] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("course_id", "checksum", name="uq_document_course_checksum"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DocumentChunk(Base):
    """Durable chunk cache used by the local keyword fallback and repair tools."""

    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_chunk_course_document", "course_id", "document_id"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(255))
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slide: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_json: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversation_course_user", "course_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_message_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    source_document_ids: Mapped[list[str]] = mapped_column(JSON)
    question_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="generating")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    questions: Mapped[list[Question]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_no"
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("quiz_id", "order_no", name="uq_question_order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    order_no: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))
    stem: Mapped[str] = mapped_column(Text)
    options_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    knowledge_tags: Mapped[list[str]] = mapped_column(JSON)
    citations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_answer_question"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"))
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    user_answer: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float] = mapped_column(Float)


class WrongItem(Base):
    __tablename__ = "wrong_items"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_wrong_item_user_question"),
        Index("ix_wrong_item_course_user", "course_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    knowledge_tag: Mapped[str] = mapped_column(String(100))
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0)
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ReviewCompletion(Base):
    __tablename__ = "review_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "wrong_item_id", "week_start", name="uq_review_completion"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    wrong_item_id: Mapped[str] = mapped_column(ForeignKey("wrong_items.id", ondelete="CASCADE"))
    week_start: Mapped[str] = mapped_column(String(10))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AiCallLog(Base):
    __tablename__ = "ai_call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    operation: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
