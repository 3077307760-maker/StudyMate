"""Conversation, streaming answer, and feedback services."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import literal_column, select
from sqlalchemy.orm import Session

from app.ai import AiProvider
from app.core.errors import AppError
from app.models import Conversation, Feedback, Message
from app.repositories import get_conversation_for_owner, require_member
from app.schemas import AskRequest, ConversationCreate, FeedbackRequest
from app.services.retrieval_service import RetrievalResult, retrieve

INSUFFICIENT_MESSAGE = (
    "当前课程资料中没有找到足够依据，暂时无法可靠回答。请补充相关课件，或换一种问法。"
)


def create_conversation(
    db: Session, course_id: str, user_id: str, payload: ConversationCreate
) -> Conversation:
    require_member(db, course_id, user_id)
    conversation = Conversation(course_id=course_id, user_id=user_id, title=payload.title.strip())
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session, course_id: str, user_id: str) -> list[Conversation]:
    require_member(db, course_id, user_id)
    return list(
        db.scalars(
            select(Conversation)
            .where(Conversation.course_id == course_id, Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
    )


def list_messages(db: Session, conversation_id: str, user_id: str) -> list[Message]:
    conversation = get_conversation_for_owner(db, conversation_id, user_id)
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at, literal_column("messages.rowid"))
        )
    )


def stream_answer(
    db: Session,
    conversation_id: str,
    user_id: str,
    payload: AskRequest,
) -> Iterator[str]:
    conversation = get_conversation_for_owner(db, conversation_id, user_id)
    question = payload.question.strip()
    user_message = Message(conversation_id=conversation.id, role="user", content=question)
    db.add(user_message)
    if conversation.title == "新会话":
        conversation.title = question[:40]
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_message)

    retrieval = retrieve(db, conversation.course_id, question)
    yield _sse("retrieval", {"status": "completed", "hit_count": len(retrieval.hits)})
    if not retrieval.sufficient:
        assistant = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=INSUFFICIENT_MESSAGE,
            citations_json=[],
            prompt_version="chat-v1",
            model_name="none",
        )
        db.add(assistant)
        db.commit()
        db.refresh(assistant)
        yield _sse(
            "error",
            {
                "code": "INSUFFICIENT_CONTEXT",
                "message": INSUFFICIENT_MESSAGE,
                "message_id": assistant.id,
            },
        )
        yield _sse(
            "done", {"message_id": assistant.id, "usage": {"input_tokens": 0, "output_tokens": 0}}
        )
        return

    for citation in retrieval.citations:
        yield _sse("citation", _public_citation(citation))

    started = time.perf_counter()
    content_parts: list[str] = []
    usage: dict[str, int] | None = None
    try:
        for text, item_usage in AiProvider().stream_answer(question, retrieval.citations):
            if text:
                content_parts.append(text)
                yield _sse("token", {"text": text})
            if item_usage:
                usage = item_usage
    except AppError as exc:
        yield _sse("error", {"code": exc.code, "message": exc.message})
        return

    content = "".join(content_parts).strip()
    if not content:
        content = INSUFFICIENT_MESSAGE
        retrieval = RetrievalResult(hits=[], citations=[])
    latency_ms = int((time.perf_counter() - started) * 1000)
    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=content,
        citations_json=retrieval.citations,
        model_name="local-extractive" if not AiProvider().enabled else "configured-model",
        prompt_version="chat-v1",
        input_tokens=(usage or {}).get("input_tokens"),
        output_tokens=(usage or {}).get("output_tokens"),
        latency_ms=latency_ms,
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    yield _sse("done", {"message_id": assistant.id, "usage": usage or {}})


def save_feedback(
    db: Session,
    message_id: str,
    user_id: str,
    payload: FeedbackRequest,
) -> Feedback:
    message = db.get(Message, message_id)
    if not message:
        raise AppError("NOT_FOUND", "消息不存在。", 404)
    conversation = get_conversation_for_owner(db, message.conversation_id, user_id)
    if conversation.user_id != user_id:
        raise AppError("FORBIDDEN", "不能评价他人的回答。", 403)
    feedback = db.scalar(
        select(Feedback).where(Feedback.message_id == message_id, Feedback.user_id == user_id)
    )
    if feedback:
        feedback.rating = payload.rating
        feedback.reason = payload.reason
    else:
        feedback = Feedback(
            message_id=message_id,
            user_id=user_id,
            rating=payload.rating,
            reason=payload.reason,
        )
        db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def _public_citation(citation: dict[str, object]) -> dict[str, object]:
    return {
        "index": citation["index"],
        "chunk_id": citation["chunk_id"],
        "document_id": citation["document_id"],
        "file_name": citation["file_name"],
        "page": citation.get("page"),
        "slide": citation.get("slide"),
        "section": citation.get("section"),
        "snippet": citation["snippet"],
    }


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
