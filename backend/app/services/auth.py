"""认证服务：签发、轮换与吊销令牌。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.token import (
    create_access_token,
    generate_refresh_token,
    hash_token,
    refresh_token_expiry,
)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_in: int


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """SQLite 返回 naive 时间，统一按 UTC 处理以便比较。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def issue_token_pair(db: Session, user: User) -> TokenPair:
    settings = get_settings()
    access_token, expires_in = create_access_token(user.id)
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            expires_at=refresh_token_expiry(),
        )
    )
    db.commit()
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=expires_in,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
    )


def _find_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
    return db.scalar(stmt)


def revoke_all_refresh_tokens(db: Session, user_id) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    now = _now()
    for token in db.scalars(stmt):
        token.revoked_at = now
    db.commit()


def rotate_refresh_token(db: Session, raw_token: str) -> TokenPair:
    token = _find_refresh_token(db, raw_token)
    if token is None:
        raise AppError(401, ErrorCode.TOKEN_INVALID, "刷新令牌无效")

    if token.revoked_at is not None or token.used_at is not None:
        # 令牌可能已泄露：吊销该用户当前全部会话，强制重新登录
        revoke_all_refresh_tokens(db, token.user_id)
        raise AppError(401, ErrorCode.REFRESH_TOKEN_REUSED, "刷新令牌已被使用，已强制退出登录")

    if _as_utc(token.expires_at) <= _now():
        raise AppError(401, ErrorCode.TOKEN_EXPIRED, "刷新令牌已过期，请重新登录")

    token.used_at = _now()
    db.add(token)
    pair = issue_token_pair(db, token.user)
    db.commit()
    return pair


def logout(db: Session, raw_token: str | None) -> None:
    """无论令牌是否有效都返回成功，不泄露其当前状态。"""
    if not raw_token:
        return
    token = _find_refresh_token(db, raw_token)
    if token is None:
        return
    token.revoked_at = _now()
    db.add(token)
    db.commit()
