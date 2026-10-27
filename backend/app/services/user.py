"""用户读写服务。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.services.password import dummy_verify, hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    return db.scalar(stmt)


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise AppError(409, ErrorCode.EMAIL_ALREADY_REGISTERED, "该邮箱已被注册")

    user = User(email=normalized_email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = get_user_by_email(db, normalized_email)
    if user is None:
        # 与「密码错误」保持同一量级的耗时，避免通过响应时间判断邮箱是否注册
        dummy_verify(password)
        raise AppError(401, ErrorCode.INVALID_CREDENTIALS, "邮箱或密码错误")

    if not verify_password(password, user.password_hash):
        raise AppError(401, ErrorCode.INVALID_CREDENTIALS, "邮箱或密码错误")

    return user
