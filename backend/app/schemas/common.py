"""通用响应结构。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """统一错误响应格式。"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "trace_id": "9f2c1a",
        }
    })

    code: str
    message: str
    trace_id: str | None = None
    details: list[dict] | None = None
