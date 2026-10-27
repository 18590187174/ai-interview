"""令牌签发与校验：Access Token 为无状态 JWT，Refresh Token 为高熵随机串。"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


def hash_token(raw_token: str) -> str:
    """库中只保存令牌哈希，数据库泄露也无法直接换取访问令牌。"""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.access_token_ttl_seconds
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise AppError(401, ErrorCode.TOKEN_EXPIRED, "访问令牌已过期") from exc
    except InvalidTokenError as exc:
        raise AppError(401, ErrorCode.TOKEN_INVALID, "访问令牌无效") from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise AppError(401, ErrorCode.TOKEN_INVALID, "访问令牌无效")
    try:
        return uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise AppError(401, ErrorCode.TOKEN_INVALID, "访问令牌无效") from exc


def refresh_token_expiry() -> datetime:
    settings = get_settings()
    return _now() + timedelta(seconds=settings.refresh_token_ttl_seconds)
