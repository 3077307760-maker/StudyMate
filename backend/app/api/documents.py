"""Document upload, status, reindex, and deletion routes."""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import Document, User
from app.schemas import DocumentOut
from app.services import (
    create_document,
    delete_document,
    get_document,
    list_documents,
    process_document,
    reindex_document,
)

course_router = APIRouter(prefix="/courses/{course_id}/documents", tags=["documents"])
router = APIRouter(prefix="/documents", tags=["documents"])


@course_router.post("", response_model=DocumentOut, status_code=202)
async def upload_document(
    course_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    content = await file.read(settings.max_upload_bytes + 1)
    document = create_document(db, course_id, user.id, file, content)
    background_tasks.add_task(process_document, document.id)
    return document


@course_router.get("", response_model=list[DocumentOut])
def list_course_documents(
    course_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Document]:
    return list_documents(db, course_id, user.id)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document_status(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    return get_document(db, document_id, user.id)


@router.post("/{document_id}/reindex", response_model=DocumentOut, status_code=202)
def reindex(
    document_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    document = reindex_document(db, document_id, user.id)
    background_tasks.add_task(process_document, document.id)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    delete_document(db, document_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
