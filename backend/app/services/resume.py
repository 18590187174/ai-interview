"""简历管理业务逻辑：上传校验、解析状态回填、属主隔离与彻底删除。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.models.resume import Resume
from app.models.user import User
from app.services.parser import parse_document
from app.services.storage import Storage

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}


def _extension(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def upload_resume(
    db: Session,
    *,
    user: User,
    filename: str,
    content: bytes,
    content_type: str | None,
    storage: Storage,
    settings: Settings,
) -> Resume:
    if _extension(filename) not in ALLOWED_EXTENSIONS:
        raise AppError(
            415,
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "简历仅支持 PDF、DOCX、TXT 格式",
        )

    if len(content) > settings.upload_max_size_bytes:
        raise AppError(
            413,
            ErrorCode.FILE_TOO_LARGE,
            f"简历文件不能超过 {settings.upload_max_size_mb}MB",
        )

    quota = (
        db.query(func.count(Resume.id)).filter(Resume.owner_id == user.id).scalar() or 0
    )
    if quota >= settings.resume_quota_per_user:
        raise AppError(
            409,
            ErrorCode.RESUME_QUOTA_EXCEEDED,
            f"最多保存 {settings.resume_quota_per_user} 份简历，请先删除不需要的简历",
        )

    stored_path = storage.save("resumes", str(user.id), filename, content)
    parsed = parse_document(filename, content)

    resume = Resume(
        owner_id=user.id,
        original_name=filename,
        stored_path=stored_path,
        size_bytes=len(content),
        content_type=content_type or "application/octet-stream",
        parse_status="succeeded" if parsed.ok else "failed",
        parse_error=None if parsed.ok else parsed.reason,
        parsed_text=parsed.text if parsed.ok else None,
        parsed_at=datetime.now(UTC) if parsed.ok else None,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def list_resumes(db: Session, owner_id: uuid.UUID) -> list[Resume]:
    return db.query(Resume).filter(Resume.owner_id == owner_id).all()


def get_owned_resume(db: Session, owner_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    # 属主隔离：他人资源一律按不存在处理，不泄露存在性
    if resume is None or resume.owner_id != owner_id:
        raise AppError(404, ErrorCode.NOT_FOUND, "简历不存在")
    return resume


def get_resume_preview(db: Session, owner_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
    """预览解析文本；解析失败的简历不可预览，返回失败原因。"""
    resume = get_owned_resume(db, owner_id, resume_id)
    if resume.parse_status != "succeeded" or not resume.parsed_text:
        raise AppError(
            409,
            ErrorCode.RESUME_NOT_PARSED,
            resume.parse_error or "简历尚未成功解析，无法预览",
        )
    return resume


def delete_resume(
    db: Session, *, owner_id: uuid.UUID, resume_id: uuid.UUID, storage: Storage
) -> None:
    resume = get_owned_resume(db, owner_id, resume_id)
    storage.delete(resume.stored_path)
    db.delete(resume)
    db.commit()
