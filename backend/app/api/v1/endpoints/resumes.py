"""简历管理端点。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_storage
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.resume import ResumeOut
from app.services import resume as resume_service
from app.services.storage import Storage

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ResumeOut)
def upload_resume(
    file: UploadFile = File(..., description="简历文件（PDF/DOCX/TXT，≤10MB）"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> ResumeOut:
    content = file.file.read()
    resume = resume_service.upload_resume(
        db,
        user=user,
        filename=file.filename or "unnamed",
        content=content,
        content_type=file.content_type,
        storage=storage,
        settings=settings,
    )
    return ResumeOut.model_validate(resume)


@router.get("", response_model=list[ResumeOut])
def list_resumes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResumeOut]:
    resumes = resume_service.list_resumes(db, user.id)
    return [ResumeOut.model_validate(item) for item in resumes]


@router.get("/{resume_id}/preview")
def preview_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    resume = resume_service.get_resume_preview(db, user.id, resume_id)
    return {
        "id": resume.id,
        "original_name": resume.original_name,
        "parsed_text": resume.parsed_text,
    }


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> None:
    resume_service.delete_resume(db, owner_id=user.id, resume_id=resume_id, storage=storage)
