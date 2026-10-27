"""知识库文档管理：上传分块、可见范围、删除与关键词检索。"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.user import User
from app.services.parser import parse_document
from app.services.storage import Storage

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50


def _extension(filename: str) -> str:
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def split_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """滑窗切分文本为重叠片段。"""
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def upload_document(
    db: Session,
    *,
    user: User,
    filename: str,
    content: bytes,
    content_type: str | None,
    is_public: bool,
    storage: Storage,
    settings: Settings,
) -> KnowledgeDocument:
    if _extension(filename) not in ALLOWED_EXTENSIONS:
        raise AppError(
            415,
            ErrorCode.UNSUPPORTED_FILE_TYPE,
            "知识库文档仅支持 PDF、DOCX、TXT、MD 格式",
        )

    if len(content) > settings.upload_max_size_bytes:
        raise AppError(
            413,
            ErrorCode.FILE_TOO_LARGE,
            f"文档不能超过 {settings.upload_max_size_mb}MB",
        )

    stored_path = storage.save("knowledge", str(user.id), filename, content)
    parsed = parse_document(filename, content)

    document = KnowledgeDocument(
        owner_id=user.id,
        name=filename,
        stored_path=stored_path,
        size_bytes=len(content),
        content_type=content_type or "application/octet-stream",
        is_public=is_public,
        retrievable=parsed.ok,
        parse_error=None if parsed.ok else parsed.reason,
    )
    db.add(document)
    db.flush()

    if parsed.ok:
        for index, chunk in enumerate(split_chunks(parsed.text)):
            db.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                )
            )

    db.commit()
    db.refresh(document)
    return document


def list_visible_documents(db: Session, user: User) -> list[KnowledgeDocument]:
    """公开文档 ∪ 本人上传的文档。"""
    return (
        db.query(KnowledgeDocument)
        .filter(
            or_(
                KnowledgeDocument.is_public.is_(True),
                KnowledgeDocument.owner_id == user.id,
            )
        )
        .all()
    )


def get_visible_document(
    db: Session, user: User, document_id: uuid.UUID
) -> KnowledgeDocument | None:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if document is None:
        return None
    if document.is_public or document.owner_id == user.id:
        return document
    # 他人私有文档按不存在处理，不泄露存在性
    return None


def delete_document(
    db: Session, *, user: User, document_id: uuid.UUID, storage: Storage
) -> None:
    document = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if document is None:
        raise AppError(404, ErrorCode.NOT_FOUND, "文档不存在")
    if document.owner_id != user.id:
        raise AppError(403, ErrorCode.FORBIDDEN, "只能删除自己上传的文档")

    storage.delete(document.stored_path)
    db.delete(document)  # 分片随 CASCADE 一并删除
    db.commit()


def extract_terms(text: str, max_terms: int = 40) -> list[str]:
    """从岗位信息中提取检索词：英文单词 + 中文二元组。"""
    words = re.findall(r"[A-Za-z]{2,}|\d{2,}", text)
    segments = re.findall(r"[\u4e00-\u9fff]+", text)
    grams: list[str] = []
    for segment in segments:
        if len(segment) == 1:
            grams.append(segment)
        else:
            grams.extend(segment[i : i + 2] for i in range(len(segment) - 1))
    seen: dict[str, None] = {}
    for term in words + grams:
        seen.setdefault(term.lower(), None)
    return list(seen)[:max_terms]


def retrieve_chunks(
    db: Session,
    *,
    user: User,
    target_role: str,
    job_description: str,
    limit: int = 6,
) -> list[tuple[KnowledgeChunk, KnowledgeDocument]]:
    """在可见且可检索的文档片段中按关键词重合度打分，返回 Top-N。"""
    visible = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.retrievable.is_(True),
            or_(
                KnowledgeDocument.is_public.is_(True),
                KnowledgeDocument.owner_id == user.id,
            ),
        )
        .all()
    )
    if not visible:
        return []

    terms = extract_terms(target_role) + extract_terms(job_description)
    if not terms:
        return []

    rows = (
        db.query(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .filter(KnowledgeChunk.document_id.in_([doc.id for doc in visible]))
        .all()
    )

    scored: list[tuple[int, int, KnowledgeChunk, KnowledgeDocument]] = []
    for order, (chunk, document) in enumerate(rows):
        lowered = chunk.content.lower()
        score = sum(lowered.count(term) for term in terms)
        if score > 0:
            scored.append((-score, order, chunk, document))

    scored.sort(key=lambda item: (item[0], item[1]))
    return [(chunk, document) for _, _, chunk, document in scored[:limit]]


def count_chunks(db: Session, document_id: uuid.UUID) -> int:
    return (
        db.query(func.count(KnowledgeChunk.id))
        .filter(KnowledgeChunk.document_id == document_id)
        .scalar()
        or 0
    )
