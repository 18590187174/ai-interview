"""健康检查：无需认证，用于探活与部署编排。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.trace import get_trace_id

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    summary="健康检查",
    responses={200: {"description": "服务正常"}, 503: {"description": "依赖不可用"}},
)
def health(response: Response, db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except SQLAlchemyError:
        logger.exception("数据库健康检查失败")
        database_status = "unavailable"

    healthy = database_status == "ok"
    response.status_code = 200 if healthy else 503
    return {
        "status": "ok" if healthy else "degraded",
        "database": database_status,
        "trace_id": get_trace_id(),
    }
