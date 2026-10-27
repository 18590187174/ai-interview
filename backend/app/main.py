"""应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import TraceIdMiddleware

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = "admin@qq.com"
DEFAULT_ADMIN_PASSWORD = "admin123"


def ensure_default_admin() -> None:
    """幂等创建默认管理员：已存在（含已改密）时完全不动。"""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.user import User
    from app.services.password import hash_password

    with SessionLocal() as db:
        exists = db.scalar(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
        if exists is not None:
            return
        db.add(
            User(
                email=DEFAULT_ADMIN_EMAIL,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                email_verified=True,
                is_admin=True,
            )
        )
        db.commit()
        logger.info("已创建默认管理员账号 %s（请尽快修改默认密码）", DEFAULT_ADMIN_EMAIL)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    ensure_default_admin()
    yield


def create_app() -> FastAPI:
    # 缺少必需配置时在此失败并指明缺失项，避免带着不完整配置启动
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI 模拟面试平台后端服务",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    app.add_middleware(TraceIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
