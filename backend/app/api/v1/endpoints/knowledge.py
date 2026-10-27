"""知识库文档端点。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_storage
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.knowledge import KnowledgeDocumentOut
from app.services import knowledge as knowledge_service
from app.services.storage import Storage

router = APIRouter(prefix="/knowledge/documents", tags=["knowledge"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=KnowledgeDocumentOut)
def upload_document(
    file: UploadFile = File(..., description="知识库文档（PDF/DOCX/TXT/MD，≤10MB）"),
    is_public: bool = Form(default=False, description="是否设为公开文档"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> KnowledgeDocumentOut:
    content = file.file.read()
    document = knowledge_service.upload_document(
        db,
        user=user,
        filename=file.filename or "unnamed",
        content=content,
        content_type=file.content_type,
        is_public=is_public,
        storage=storage,
        settings=settings,
    )
    return KnowledgeDocumentOut.model_validate(document)


@router.get("", response_model=list[KnowledgeDocumentOut])
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeDocumentOut]:
    documents = knowledge_service.list_visible_documents(db, user)
    return [KnowledgeDocumentOut.model_validate(item) for item in documents]


@router.get("/{document_id}", response_model=KnowledgeDocumentOut)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeDocumentOut:
    document = knowledge_service.get_visible_document(db, user, document_id)
    if document is None:
        from app.core.errors import AppError, ErrorCode

        raise AppError(404, ErrorCode.NOT_FOUND, "文档不存在")
    return KnowledgeDocumentOut.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> None:
    knowledge_service.delete_document(
        db, user=user, document_id=document_id, storage=storage
    )
