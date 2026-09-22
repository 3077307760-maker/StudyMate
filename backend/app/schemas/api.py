"""Pydantic request and response contracts for the public API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORMModel):
    id: str
    email: str
    display_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CourseJoin(BaseModel):
    invite_code: str = Field(min_length=6, max_length=6)

    @field_validator("invite_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseOut(ORMModel):
    id: str
    name: str
    invite_code: str
    owner_id: str
    role: str
    created_at: datetime


class MemberOut(BaseModel):
    id: str
    display_name: str
    email: str
    role: str
    joined_at: datetime


class CourseStatsOut(BaseModel):
    document_count: int
    ready_document_count: int
    member_count: int
    conversation_count: int
    quiz_count: int
    wrong_item_count: int


class DocumentOut(ORMModel):
    id: str
    course_id: str
    original_name: str
    mime_type: str
    size_bytes: int
    checksum: str
    status: str
    error_message: str | None
    chunk_count: int
    created_by: str
    created_at: datetime
    processed_at: datetime | None


class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=100)


class ConversationOut(ORMModel):
    id: str
    course_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class CitationOut(BaseModel):
    index: int
    chunk_id: str
    document_id: str
    file_name: str
    page: int | None = None
    slide: int | None = None
    section: str | None = None
    snippet: str


class MessageOut(ORMModel):
    id: str
    conversation_id: str
    role: str
    content: str
    citations_json: list[dict[str, Any]] | None
    model_name: str | None
    prompt_version: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    created_at: datetime


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class FeedbackRequest(BaseModel):
    rating: Literal["helpful", "inaccurate"]
    reason: str | None = Field(default=None, max_length=500)


class FeedbackOut(ORMModel):
    id: str
    message_id: str
    rating: str
    reason: str | None
    created_at: datetime


def _default_question_types() -> list[Literal["single_choice", "short_answer"]]:
    return ["single_choice", "short_answer"]


class QuizCreate(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=10)
    question_count: Literal[5, 10] = 5
    question_types: list[Literal["single_choice", "short_answer"]] = Field(
        default_factory=_default_question_types, min_length=1
    )
    chapter: str | None = Field(default=None, max_length=100)


class QuestionPublicOut(BaseModel):
    id: str
    order_no: int
    type: str
    stem: str
    options: list[str] | None
    knowledge_tags: list[str]


class QuizPublicOut(BaseModel):
    id: str
    course_id: str
    title: str
    status: str
    question_count: int
    created_at: datetime
    questions: list[QuestionPublicOut]


class AnswerSubmission(BaseModel):
    question_id: str
    answer: str = Field(max_length=2000)


class QuizSubmitRequest(BaseModel):
    answers: list[AnswerSubmission]


class AnswerResult(BaseModel):
    question_id: str
    user_answer: str
    is_correct: bool | None
    score: float
    correct_answer: str
    explanation: str
    citations: list[dict[str, Any]]


class QuizResultOut(BaseModel):
    attempt_id: str
    score: float
    max_score: float
    answers: list[AnswerResult]


class WrongPracticeOut(BaseModel):
    wrong_item_id: str
    question: QuestionPublicOut
    answer_count: int


class WrongItemOut(BaseModel):
    id: str
    course_id: str
    question_id: str
    knowledge_tag: str
    wrong_count: int
    consecutive_correct: int
    mastered: bool
    last_wrong_at: datetime
    question: QuestionPublicOut


class ReviewTaskOut(BaseModel):
    wrong_item_id: str
    knowledge_tag: str
    question: QuestionPublicOut
    wrong_count: int
    priority: int
    completed: bool


class ReviewPlanOut(BaseModel):
    week_start: str
    tasks: list[ReviewTaskOut]
    total: int
    completed: int


class HealthOut(BaseModel):
    status: str
    database: str
    vector_store: str
