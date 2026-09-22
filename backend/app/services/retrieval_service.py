"""Evidence retrieval and citation construction."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import VectorHit, get_vector_index
from app.core.config import settings
from app.models import Document

EVIDENCE_THRESHOLD = 0.35
LOCAL_FALLBACK_THRESHOLD = 0.25
CANDIDATE_LIMIT = 12
FINAL_CONTEXT_LIMIT = 4


@dataclass(slots=True)
class RetrievalResult:
    hits: list[VectorHit]
    citations: list[dict[str, object]]
    enforce_threshold: bool = True

    @property
    def sufficient(self) -> bool:
        if not self.hits:
            return False
        use_semantic_threshold = settings.enable_chroma and settings.embedding_provider != "local"`n        threshold = EVIDENCE_THRESHOLD if use_semantic_threshold else LOCAL_FALLBACK_THRESHOLD
        return not self.enforce_threshold or self.hits[0].score >= threshold


def retrieve(
    db: Session,
    course_id: str,
    query: str,
    document_ids: set[str] | None = None,
    enforce_threshold: bool = True,
) -> RetrievalResult:
    ready_statement = select(func.count()).select_from(Document).where(
        Document.course_id == course_id, Document.status == "ready"
    )
    if document_ids:
        ready_statement = ready_statement.where(Document.id.in_(document_ids))
    ready_count = int(db.scalar(ready_statement) or 0)
    if ready_count == 0:
        return RetrievalResult(hits=[], citations=[], enforce_threshold=enforce_threshold)
    hits = get_vector_index().search(
        db,
        course_id,
        query,
        CANDIDATE_LIMIT,
        document_ids=document_ids,
    )
    selected = [hit for hit in hits if hit.score > 0][:FINAL_CONTEXT_LIMIT]
    if not selected and not enforce_threshold:
        selected = hits[:FINAL_CONTEXT_LIMIT]
    citations = [
        {
            "index": index,
            "chunk_id": hit.chunk_id,
            "document_id": hit.document_id,
            "file_name": hit.file_name,
            "page": hit.page,
            "slide": hit.slide,
            "section": hit.section,
            "snippet": hit.content[:600],
            "score": round(hit.score, 4),
        }
        for index, hit in enumerate(selected, start=1)
    ]
    return RetrievalResult(
        hits=selected,
        citations=citations,
        enforce_threshold=enforce_threshold,
    )
