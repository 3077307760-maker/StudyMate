"""Quiz, wrong-item practice, and weekly review routes."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    AnswerResult,
    QuizCreate,
    QuizPublicOut,
    QuizResultOut,
    QuizSubmitRequest,
    ReviewCompletionOut,
    ReviewPlanOut,
    WrongItemOut,
    WrongPracticeOut,
    WrongPracticeSubmit,
)
from app.services import (
    complete_review_item,
    create_quiz,
    get_quiz,
    list_wrong_items,
    practice_wrong_item,
    review_plan,
    submit_quiz,
    submit_wrong_practice,
)

course_router = APIRouter(prefix="/courses/{course_id}", tags=["quiz", "review"])
quiz_router = APIRouter(prefix="/quizzes", tags=["quiz"])
wrong_router = APIRouter(tags=["review"])


@course_router.post("/quizzes", response_model=QuizPublicOut, status_code=201)
def generate(
    course_id: str,
    payload: QuizCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return create_quiz(db, course_id, user.id, payload)


@course_router.get("/wrong-items", response_model=list[WrongItemOut])
def wrong_items(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return list_wrong_items(db, course_id, user.id)


@course_router.get("/review-plan", response_model=ReviewPlanOut)
def weekly_review(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return review_plan(db, course_id, user.id)


@quiz_router.get("/{quiz_id}", response_model=QuizPublicOut)
def detail(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_quiz(db, quiz_id, user.id)


@quiz_router.post("/{quiz_id}/submit", response_model=QuizResultOut)
def submit(
    quiz_id: str,
    payload: QuizSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return submit_quiz(db, quiz_id, user.id, payload)


@wrong_router.post("/wrong-items/{wrong_item_id}/practice", response_model=WrongPracticeOut)
def practice(
    wrong_item_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WrongPracticeOut:
    return practice_wrong_item(db, wrong_item_id, user.id)

@wrong_router.post("/wrong-items/{wrong_item_id}/answer", response_model=AnswerResult)
def answer_wrong_item(
    wrong_item_id: str,
    payload: WrongPracticeSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return submit_wrong_practice(db, wrong_item_id, user.id, payload.answer)


@wrong_router.post("/review-items/{wrong_item_id}/complete", response_model=ReviewCompletionOut)
def complete_review(
    wrong_item_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return complete_review_item(db, wrong_item_id, user.id)
