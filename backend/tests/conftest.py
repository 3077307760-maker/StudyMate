"""Shared test configuration with an isolated SQLite database."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEMP_ROOT = Path(tempfile.mkdtemp(prefix="studymate-tests-"))
os.environ["APP_ENV"] = "test"
os.environ["APP_SECRET_KEY"] = "test-secret-key-that-is-long-enough"
os.environ["DATABASE_URL"] = f"sqlite:///{(TEMP_ROOT / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEMP_ROOT / "uploads")
os.environ["ENABLE_CHROMA"] = "false"
os.environ["LLM_API_KEY"] = ""

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str, name: str = "测试用户") -> dict[str, str]:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "display_name": name},
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_course(client: TestClient, headers: dict[str, str], name: str = "操作系统") -> dict:
    response = client.post("/api/courses", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def upload_markdown(
    client: TestClient,
    headers: dict[str, str],
    course_id: str,
    content: str,
    filename: str = "操作系统笔记.md",
) -> dict:
    response = client.post(
        f"/api/courses/{course_id}/documents",
        files={"file": (filename, content.encode("utf-8"), "text/markdown")},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    return response.json()
