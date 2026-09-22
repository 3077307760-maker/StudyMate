"""Vector index implementations: ChromaDB in production and SQLite locally."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.providers import AiProvider, _tokens
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import DocumentChunk


@dataclass(slots=True)
class IndexChunk:
    id: str
    course_id: str
    document_id: str
    file_name: str
    page: int | None
    slide: int | None
    section: str | None
    content: str
    content_hash: str
    embedding: list[float]


@dataclass(slots=True)
class VectorHit:
    chunk_id: str
    document_id: str
    file_name: str
    page: int | None
    slide: int | None
    section: str | None
    content: str
    score: float


class VectorIndex(Protocol):
    def upsert_document(self, db: Session, chunks: list[IndexChunk]) -> None: ...

    def delete_document(self, document_id: str) -> None: ...

    def search(
        self,
        db: Session,
        course_id: str,
        query: str,
        limit: int,
        document_ids: set[str] | None = None,
    ) -> list[VectorHit]: ...

    def health(self) -> str: ...


class LocalVectorIndex:
    """Persistent fallback used in tests and local no-Chroma development."""

    def upsert_document(self, db: Session, chunks: list[IndexChunk]) -> None:
        if not chunks:
            return
        document_id = chunks[0].document_id
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        db.add_all(
            [
                DocumentChunk(
                    id=chunk.id,
                    course_id=chunk.course_id,
                    document_id=chunk.document_id,
                    file_name=chunk.file_name,
                    page=chunk.page,
                    slide=chunk.slide,
                    section=chunk.section,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    embedding_json=chunk.embedding,
                )
                for chunk in chunks
            ]
        )

    def delete_document(self, document_id: str) -> None:
        with SessionLocal() as db:
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
            db.commit()

    def search(
        self,
        db: Session,
        course_id: str,
        query: str,
        limit: int,
        document_ids: set[str] | None = None,
    ) -> list[VectorHit]:
        statement = select(DocumentChunk).where(DocumentChunk.course_id == course_id)
        if document_ids:
            statement = statement.where(DocumentChunk.document_id.in_(document_ids))
        chunks = list(db.scalars(statement.order_by(DocumentChunk.created_at.desc())))
        if not chunks:
            return []
        query_tokens = set(_tokens(query))
        query_embedding = AiProvider().embed([query])[0]
        hits: list[VectorHit] = []
        for chunk in chunks:
            keyword_score = _keyword_score(query_tokens, set(_tokens(chunk.content)))
            vector_score = max(0.0, cosine(query_embedding, chunk.embedding_json or []))
            score = 0.0 if keyword_score == 0 else 0.75 * keyword_score + 0.25 * vector_score
            hits.append(
                VectorHit(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    file_name=chunk.file_name,
                    page=chunk.page,
                    slide=chunk.slide,
                    section=chunk.section,
                    content=chunk.content,
                    score=score,
                )
            )
        return sorted(hits, key=lambda item: item.score, reverse=True)[:limit]

    def health(self) -> str:
        return "sqlite"


class ChromaVectorIndex:
    def __init__(self, base_url: str, collection_name: str = "studymate_chunks") -> None:
        self.base_url = base_url.rstrip("/")
        self.collection_name = collection_name
        self.client = httpx.Client(base_url=self.base_url, timeout=20)
        self.collection_id: str | None = None

    def _collection(self) -> str:
        if self.collection_id and self._collection_exists(self.collection_id):
            return self.collection_id
        response = self.client.post(
            "/api/v1/collections",
            json={
                "name": self.collection_name,
                "get_or_create": True,
                "metadata": {"hnsw:space": "cosine"},
            },
        )
        response.raise_for_status()
        self.collection_id = str(response.json()["id"])
        return self.collection_id

    def _collection_exists(self, collection_id: str) -> bool:
        try:
            response = self.client.get(f"/api/v1/collections/{collection_id}")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def upsert_document(self, db: Session, chunks: list[IndexChunk]) -> None:
        if not chunks:
            return
        collection_id = self._collection()
        self.delete_document(chunks[0].document_id)
        response = self.client.post(
            f"/api/v1/collections/{collection_id}/add",
            json={
                "ids": [chunk.id for chunk in chunks],
                "embeddings": [chunk.embedding for chunk in chunks],
                "documents": [chunk.content for chunk in chunks],
                "metadatas": [
                    {
                        "course_id": chunk.course_id,
                        "document_id": chunk.document_id,
                        "file_name": chunk.file_name,
                        "page": chunk.page or 0,
                        "slide": chunk.slide or 0,
                        "section": chunk.section or "",
                        "content_hash": chunk.content_hash,
                    }
                    for chunk in chunks
                ],
            },
        )
        response.raise_for_status()

    def delete_document(self, document_id: str) -> None:
        collection_id = self._collection()
        response = self.client.post(
            f"/api/v1/collections/{collection_id}/delete",
            json={"where": {"document_id": document_id}},
        )
        if response.status_code not in {200, 204, 404}:
            response.raise_for_status()

    def search(
        self,
        db: Session,
        course_id: str,
        query: str,
        limit: int,
        document_ids: set[str] | None = None,
    ) -> list[VectorHit]:
        collection_id = self._collection()
        embedding = AiProvider().embed([query])[0]
        response = self.client.post(
            f"/api/v1/collections/{collection_id}/query",
            json={
                "query_embeddings": [embedding],
                "n_results": limit,
                "where": _where_filter(course_id, document_ids),
                "include": ["documents", "metadatas", "distances"],
            },
        )
        response.raise_for_status()
        payload = response.json()
        ids = (payload.get("ids") or [[]])[0]
        documents = (payload.get("documents") or [[]])[0]
        metadatas = (payload.get("metadatas") or [[]])[0]
        distances = (payload.get("distances") or [[]])[0]
        hits: list[VectorHit] = []
        for chunk_id, content, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=False
        ):
            keyword_score = _keyword_score(set(_tokens(query)), set(_tokens(content or "")))
            vector_score = max(0.0, 1.0 - float(distance))
            score = (
                keyword_score
                if settings.embedding_provider == "local"
                else 0.75 * vector_score + 0.25 * keyword_score
            )
            hits.append(
                VectorHit(
                    chunk_id=str(chunk_id),
                    document_id=str(metadata["document_id"]),
                    file_name=str(metadata["file_name"]),
                    page=int(metadata.get("page") or 0) or None,
                    slide=int(metadata.get("slide") or 0) or None,
                    section=str(metadata.get("section") or "") or None,
                    content=content or "",
                    score=score,
                )
            )
        return hits

    def health(self) -> str:
        try:
            response = self.client.get("/api/v1/heartbeat", timeout=2)
            response.raise_for_status()
            return "chroma"
        except httpx.HTTPError:
            return "chroma-unavailable"


def get_vector_index() -> VectorIndex:
    if settings.enable_chroma:
        return ChromaVectorIndex(settings.chroma_url)
    return LocalVectorIndex()


def _where_filter(course_id: str, document_ids: set[str] | None) -> dict[str, object]:
    if not document_ids:
        return {"course_id": course_id}
    values = sorted(document_ids)
    return {
        "$and": [
            {"course_id": course_id},
            {"document_id": values[0] if len(values) == 1 else {"$in": values}},
        ]
    }


def _keyword_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    if not denominator:
        return 0.0
    return sum(x * y for x, y in zip(left, right, strict=False)) / denominator
