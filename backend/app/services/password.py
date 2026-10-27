"""密码哈希：Argon2id，参数可通过配置调整。"""

from __future__ import annotations

from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings


@lru_cache
def _hasher(time_cost: int, memory_cost: int, parallelism: int) -> PasswordHasher:
    return PasswordHasher(time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism)


def get_hasher() -> PasswordHasher:
    settings = get_settings()
    return _hasher(
        settings.argon2_time_cost,
        settings.argon2_memory_cost,
        settings.argon2_parallelism,
    )


def hash_password(raw_password: str) -> str:
    return get_hasher().hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return get_hasher().verify(password_hash, raw_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_verify(raw_password: str) -> None:
    """用户不存在时做一次等价耗时的哈希校验，避免通过响应时间枚举账号。"""
    get_hasher().verify(hash_password(raw_password), raw_password)
