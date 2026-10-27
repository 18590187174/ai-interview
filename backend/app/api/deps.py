"""接口公共依赖：默认要求有效访问令牌。"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.services.storage import LocalStorage, Storage
from app.services.token import decode_access_token
from app.services.user import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False, description="Bearer Access Token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "缺少访问令牌")

    user_id = decode_access_token(credentials.credentials)
    user = get_user_by_id(db, user_id)
    if user is None:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "用户不存在或已注销")
    return user


def get_storage(settings: Settings = Depends(get_settings)) -> Storage:
    """文件存储依赖：测试可通过 dependency_overrides 注入临时目录。"""
    return LocalStorage(settings.upload_root)


def require_admin(user: User = Depends(get_current_user)) -> User:
    """管理员权限依赖：已登录但角色不足时返回 403。"""
    if not user.is_admin:
        raise AppError(403, ErrorCode.FORBIDDEN, "该操作仅管理员可用")
    return user
