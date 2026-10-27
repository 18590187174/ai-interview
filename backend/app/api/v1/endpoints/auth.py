"""认证接口：注册、登录、刷新、登出。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError, ErrorCode
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services import auth as auth_service
from app.services.auth import TokenPair
from app.services.user import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=REFRESH_COOKIE_PATH,
        domain=settings.cookie_domain,
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        domain=settings.cookie_domain,
    )


def extract_refresh_token(request: Request, provided: str | None) -> str | None:
    """优先取 httpOnly Cookie，body 仅用于非浏览器客户端。"""
    return provided or request.cookies.get(REFRESH_COOKIE_NAME)


def token_response(pair: TokenPair) -> TokenResponse:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type="bearer",
        expires_in=pair.expires_in,
        refresh_expires_in=pair.refresh_expires_in,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="注册新用户",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserRead:
    user = create_user(db, payload.email, payload.password)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="登录并获取令牌")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    pair = auth_service.issue_token_pair(db, user)
    set_refresh_cookie(response, pair.refresh_token, settings)
    return token_response(pair)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌（含轮换与重用检测）")
def refresh(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    raw_token = extract_refresh_token(request, payload.refresh_token)
    if not raw_token:
        raise AppError(401, ErrorCode.TOKEN_INVALID, "缺少刷新令牌")

    pair = auth_service.rotate_refresh_token(db, raw_token)
    set_refresh_cookie(response, pair.refresh_token, settings)
    return token_response(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="登出并吊销刷新令牌")
def logout(
    payload: LogoutRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    raw_token = extract_refresh_token(request, payload.refresh_token)
    auth_service.logout(db, raw_token)
    clear_refresh_cookie(response, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
