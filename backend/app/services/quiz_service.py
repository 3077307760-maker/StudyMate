"""Quiz generation, grading, wrong-item management, and weekly review."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import AiProvider
from app.core.errors import AppError
from app.models import (
    Attempt,
    AttemptAnswer,
    Document,
    Question,
    Quiz,
    ReviewCompletion,
    WrongItem,
)
from app.repositories import get_quiz_for_member, require_member
from app.schemas import (
    AnswerSubmission,
    QuestionPublicOut,
    QuizCreate,
    QuizSubmitRequest,
    WrongPracticeOut,
)
from app.services.retrieval_service import retrieve


def create_quiz(db: Session, course_id: str, user_id: str, payload: QuizCreate) -> dict[str, Any]:
    require_member(db, course_id, user_id)
    documents = list(
        db.scalars(
            select(Document).where(
                Document.course_id == course_id,
                Document.id.in_(payload.document_ids),
                Document.status == "ready",
            )
        )
    )
    if len(documents) != len(set(payload.document_ids)):
        raise AppError("DOCUMENT_NOT_READY", "所选文档不存在或尚未完成索引。", 409)

    allowed_ids = set(payload.document_ids)
    query_terms = " ".join(document.original_name for document in documents)
    retrieval = retrieve(
        db,
        course_id,
        f"{payload.chapter or ''} {query_terms} 核心知识点",
        document_ids=allowed_ids,
        enforce_threshold=False,
    )
    context = retrieval.citations
    if not context:
        raise AppError("INSUFFICIENT_CONTEXT", "所选资料中没有足够的可检索内容。", 422)

    quiz = Quiz(
        course_id=course_id,
        user_id=user_id,
        title=f"{payload.chapter or documents[0].original_name}练习",
        source_document_ids=payload.document_ids,
        question_count=payload.question_count,
        status="generating",
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    try:
        generated = AiProvider().generate_quiz(
            context,
            payload.question_count,
            payload.question_types,
            payload.chapter,
        )
        _validate_generated_quiz(generated, payload, context)
        for order_no, item in enumerate(generated["questions"], start=1):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    order_no=order_no,
                    type=item["type"],
                    stem=item["stem"],
                    options_json=item.get("options"),
                    correct_answer=str(item["correct_answer"]),
                    explanation=item["explanation"],
                    knowledge_tags=item["knowledge_tags"],
                    citations_json=item["citations"],
                )
            )
        quiz.status = "ready"
        quiz.title = str(generated.get("title") or quiz.title)[:100]
        db.commit()
        db.refresh(quiz)
        return quiz_public_payload(quiz)
    except Exception as exc:  # noqa: BLE001
        quiz.status = "failed"
        quiz.error_message = exc.message if isinstance(exc, AppError) else "模型输出校验失败。"
        db.commit()
        if isinstance(exc, AppError):
            exc.details["quiz_id"] = quiz.id
            raise
        raise AppError(
            "MODEL_OUTPUT_INVALID",
            "练习生成结果无法通过校验，请稍后重试。",
            502,
            {"quiz_id": quiz.id},
        ) from exc


def get_quiz(db: Session, quiz_id: str, user_id: str) -> dict[str, Any]:
    quiz = get_quiz_for_member(db, quiz_id, user_id)
    return quiz_public_payload(quiz)


def submit_quiz(
    db: Session, quiz_id: str, user_id: str, payload: QuizSubmitRequest
) -> dict[str, Any]:
    quiz = get_quiz_for_member(db, quiz_id, user_id)
    if quiz.status != "ready":
        raise AppError("QUIZ_NOT_READY", "练习尚未生成完成。", 409)
    answer_map = {answer.question_id: answer for answer in payload.answers}
    attempt = Attempt(quiz_id=quiz.id, user_id=user_id, score=0)
    db.add(attempt)
    db.flush()
    total_score = 0.0
    results: list[dict[str, Any]] = []
    for question in quiz.questions:
        submission = answer_map.get(question.id) or AnswerSubmission(
            question_id=question.id, answer=""
        )
        is_correct, score = _grade_question(question, submission.answer)
        total_score += score
        db.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                user_answer=submission.answer,
                is_correct=is_correct,
                score=score,
            )
        )
        _update_wrong_item(db, user_id, quiz.course_id, question, is_correct)
        results.append(
            {
                "question_id": question.id,
                "user_answer": submission.answer,
                "is_correct": is_correct,
                "score": score,
                "correct_answer": question.correct_answer,
                "explanation": question.explanation,
                "citations": question.citations_json,
            }
        )
    attempt.score = round(total_score / max(1, len(quiz.questions)) * 100, 2)
    db.commit()
    return {
        "attempt_id": attempt.id,
        "score": attempt.score,
        "max_score": 100.0,
        "answers": results,
    }


def list_wrong_items(db: Session, course_id: str, user_id: str) -> list[dict[str, Any]]:
    require_member(db, course_id, user_id)
    rows = db.execute(
        select(WrongItem, Question)
        .join(Question, Question.id == WrongItem.question_id)
        .where(WrongItem.course_id == course_id, WrongItem.user_id == user_id)
        .order_by(WrongItem.mastered, WrongItem.wrong_count.desc(), WrongItem.last_wrong_at.desc())
    ).all()
    return [
        {
            "id": wrong.id,
            "course_id": wrong.course_id,
            "question_id": wrong.question_id,
            "quiz_id": question.quiz_id,
            "knowledge_tag": wrong.knowledge_tag,
            "wrong_count": wrong.wrong_count,
            "consecutive_correct": wrong.consecutive_correct,
            "mastered": wrong.mastered,
            "last_wrong_at": wrong.last_wrong_at,
            "question": question_public_payload(question),
        }
        for wrong, question in rows
    ]


def practice_wrong_item(db: Session, wrong_item_id: str, user_id: str) -> WrongPracticeOut:
    wrong = db.get(WrongItem, wrong_item_id)
    if not wrong or wrong.user_id != user_id:
        raise AppError("NOT_FOUND", "错题不存在。", 404)
    question = db.get(Question, wrong.question_id)
    if not question:
        raise AppError("NOT_FOUND", "错题题目不存在。", 404)
    return WrongPracticeOut(
        wrong_item_id=wrong.id,
        question=QuestionPublicOut(**question_public_payload(question)),
        answer_count=int(
            db.scalar(
                select(func.count())
                .select_from(AttemptAnswer)
                .join(Attempt, Attempt.id == AttemptAnswer.attempt_id)
                .where(Attempt.user_id == user_id, AttemptAnswer.question_id == question.id)
            )
            or 0
        ),
    )


def review_plan(db: Session, course_id: str, user_id: str) -> dict[str, Any]:
    require_member(db, course_id, user_id)
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    wrong_items = list(
        db.scalars(
            select(WrongItem)
            .where(
                WrongItem.course_id == course_id,
                WrongItem.user_id == user_id,
                WrongItem.mastered.is_(False),
            )
            .order_by(WrongItem.wrong_count.desc(), WrongItem.last_wrong_at)
        )
    )
    completed_ids = set(
        db.scalars(
            select(ReviewCompletion.wrong_item_id).where(
                ReviewCompletion.user_id == user_id,
                ReviewCompletion.week_start == week_start,
            )
        )
    )
    tasks: list[dict[str, Any]] = []
    for wrong in wrong_items:
        question = db.get(Question, wrong.question_id)
        if not question:
            continue
        tasks.append(
            {
                "wrong_item_id": wrong.id,
                "knowledge_tag": wrong.knowledge_tag,
                "question": question_public_payload(question),
                "wrong_count": wrong.wrong_count,
                "priority": min(3, 1 + wrong.wrong_count // 2),
                "completed": wrong.id in completed_ids,
            }
        )
    return {
        "week_start": week_start,
        "tasks": tasks,
        "total": len(tasks),
        "completed": sum(1 for task in tasks if task["completed"]),
    }


def submit_wrong_practice(
    db: Session,
    wrong_item_id: str,
    user_id: str,
    answer: str,
) -> dict[str, Any]:
    wrong = db.get(WrongItem, wrong_item_id)
    if not wrong or wrong.user_id != user_id:
        raise AppError("NOT_FOUND", "错题不存在。", 404)
    question = db.get(Question, wrong.question_id)
    if not question:
        raise AppError("NOT_FOUND", "错题题目不存在。", 404)
    is_correct, score = _grade_question(question, answer)
    _update_wrong_item(db, user_id, wrong.course_id, question, is_correct)
    attempt = Attempt(quiz_id=question.quiz_id, user_id=user_id, score=score * 100)
    db.add(attempt)
    db.flush()
    db.add(
        AttemptAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            user_answer=answer,
            is_correct=is_correct,
            score=score,
        )
    )
    db.commit()
    return {
        "question_id": question.id,
        "user_answer": answer,
        "is_correct": is_correct,
        "score": score,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "citations": question.citations_json,
    }


def complete_review_item(db: Session, wrong_item_id: str, user_id: str) -> dict[str, Any]:
    wrong = db.get(WrongItem, wrong_item_id)
    if not wrong or wrong.user_id != user_id:
        raise AppError("NOT_FOUND", "错题不存在。", 404)
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    completion = db.scalar(
        select(ReviewCompletion).where(
            ReviewCompletion.user_id == user_id,
            ReviewCompletion.wrong_item_id == wrong_item_id,
            ReviewCompletion.week_start == week_start,
        )
    )
    if not completion:
        completion = ReviewCompletion(
            user_id=user_id,
            wrong_item_id=wrong_item_id,
            week_start=week_start,
        )
        db.add(completion)
        db.commit()
        db.refresh(completion)
    return {
        "wrong_item_id": wrong_item_id,
        "week_start": week_start,
        "completed_at": completion.completed_at,
    }

def question_public_payload(question: Question) -> dict[str, Any]:
    return {
        "id": question.id,
        "order_no": question.order_no,
        "type": question.type,
        "stem": question.stem,
        "options": question.options_json,
        "knowledge_tags": question.knowledge_tags,
    }


def quiz_public_payload(quiz: Quiz) -> dict[str, Any]:
    return {
        "id": quiz.id,
        "course_id": quiz.course_id,
        "title": quiz.title,
        "status": quiz.status,
        "question_count": quiz.question_count,
        "created_at": quiz.created_at,
        "questions": [question_public_payload(question) for question in quiz.questions],
    }


def _grade_question(question: Question, answer: str) -> tuple[bool | None, float]:
    normalized = answer.strip()
    if question.type == "single_choice":
        correct = normalized.upper() == question.correct_answer.strip().upper()
        return correct, 1.0 if correct else 0.0
    if not normalized:
        return False, 0.0
    user_tokens = set(_simple_tokens(normalized))
    answer_tokens = set(_simple_tokens(question.correct_answer))
    if not answer_tokens:
        return None, 0.5
    overlap = len(user_tokens & answer_tokens) / len(answer_tokens)
    if overlap >= 0.6:
        return True, 1.0
    if overlap >= 0.25:
        return None, 0.5
    return False, 0.0


def _update_wrong_item(
    db: Session,
    user_id: str,
    course_id: str,
    question: Question,
    is_correct: bool | None,
) -> None:
    wrong = db.scalar(
        select(WrongItem).where(
            WrongItem.user_id == user_id,
            WrongItem.question_id == question.id,
        )
    )
    if is_correct is None:
        return
    if is_correct:
        if wrong:
            wrong.consecutive_correct += 1
            wrong.mastered = wrong.consecutive_correct >= 2
        return
    if wrong:
        wrong.wrong_count += 1
        wrong.consecutive_correct = 0
        wrong.mastered = False
        wrong.last_wrong_at = datetime.utcnow()
    else:
        db.add(
            WrongItem(
                user_id=user_id,
                course_id=course_id,
                question_id=question.id,
                knowledge_tag=(question.knowledge_tags or ["未分类"])[0],
                wrong_count=1,
                consecutive_correct=0,
                mastered=False,
            )
        )


def _validate_generated_quiz(
    payload: dict[str, Any], request: QuizCreate, context: list[dict[str, Any]]
) -> None:
    questions = payload.get("questions")
    if not isinstance(questions, list) or len(questions) != request.question_count:
        raise ValueError("question count mismatch")
    allowed_documents: dict[str, list[dict[str, Any]]] = {}
    for item in context:
        document_id = str(item["document_id"])
        allowed_documents.setdefault(document_id, []).append(item)

    for item in questions:
        if item.get("type") not in {"single_choice", "short_answer"}:
            raise ValueError("unsupported question type")
        if not item.get("stem") or not item.get("explanation") or not item.get("knowledge_tags"):
            raise ValueError("missing question fields")
        if not item.get("citations"):
            raise ValueError("missing citations")
        if item["type"] == "single_choice":
            options = item.get("options") or []
            if len(options) != 4 or str(item.get("correct_answer", "")).upper() not in {
                "A",
                "B",
                "C",
                "D",
            }:
                raise ValueError("invalid single choice")
        for citation in item["citations"]:
            document_id = str(citation.get("document_id", ""))
            if not _citation_matches_context(citation, allowed_documents.get(document_id, [])):
                raise ValueError("citation outside retrieval context")


def _citation_matches_context(
    citation: dict[str, Any], candidates: list[dict[str, Any]]
) -> bool:
    for source in candidates:
        if citation.get("page") not in {None, source.get("page")}:
            continue
        if citation.get("slide") not in {None, source.get("slide")}:
            continue
        snippet = str(citation.get("snippet", "")).strip()
        source_snippet = str(source.get("snippet", "")).strip()
        if snippet and (snippet in source_snippet or source_snippet[:80] in snippet):
            return True
    return False


def _simple_tokens(text: str) -> list[str]:
    normalized = text.lower().replace("，", " ").replace("。", " ").replace(",", " ")
    tokens = [token for token in normalized.split() if token]
    return tokens or list(text.replace(" ", ""))
