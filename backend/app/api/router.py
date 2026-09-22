from fastapi import APIRouter

from app.api import auth, chat, courses, documents, health, quizzes

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(auth.me_router)
api_router.include_router(courses.router)
api_router.include_router(documents.course_router)
api_router.include_router(documents.router)
api_router.include_router(chat.course_router)
api_router.include_router(chat.router)
api_router.include_router(quizzes.course_router)
api_router.include_router(quizzes.quiz_router)
api_router.include_router(quizzes.wrong_router)
api_router.include_router(health.router)

__all__ = ["api_router"]
