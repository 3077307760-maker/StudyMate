"""Conversation, SSE chat, message history, and feedback routes."""

from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Conversation, Message, User
from app.schemas import (
    AskRequest,
    ConversationCreate,
    ConversationOut,
    FeedbackOut,
    FeedbackRequest,
    MessageOut,
)
from app.services import (
    create_conversation,
    list_conversations,
    list_messages,
    save_feedback,
    stream_answer,
)

course_router = APIRouter(prefix="/courses/{course_id}/conversations", tags=["chat"])
router = APIRouter(tags=["chat"])


@course_router.post("", response_model=ConversationOut, status_code=201)
def create(
    course_id: str,
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return create_conversation(db, course_id, user.id, payload)


@course_router.get("", response_model=list[ConversationOut])
def list_all(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    return list_conversations(db, course_id, user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Message]:
    return list_messages(db, conversation_id, user.id)


@router.post("/conversations/{conversation_id}/messages")
def ask(
    conversation_id: str,
    payload: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    events: Iterator[str] = stream_answer(db, conversation_id, user.id, payload)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages/{message_id}/feedback", response_model=FeedbackOut)
def feedback(
    message_id: str,
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_feedback(db, message_id, user.id, payload)
