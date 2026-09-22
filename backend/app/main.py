"""FastAPI application factory and lifecycle management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from app.api import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.errors import RequestContextMiddleware, install_error_handlers
from app.core.logging import configure_logging
from app.models import Document


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    mark_interrupted_documents_failed()
    yield


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title="StudyMate API",
        version="0.1.0",
        description="课程资料 AI 问答与错题复习助手",
        lifespan=lifespan,
    )
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    install_error_handlers(application)
    application.include_router(api_router)

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"name": "StudyMate API", "docs": "/docs", "health": "/api/health"}

    return application


def mark_interrupted_documents_failed() -> None:
    with SessionLocal() as db:
        db.execute(
            update(Document)
            .where(Document.status == "processing")
            .values(status="failed", error_message="服务重启导致索引中断，请手动重试。")
        )
        db.commit()


app = create_app()
