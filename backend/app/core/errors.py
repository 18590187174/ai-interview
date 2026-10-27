"""统一错误码与错误响应格式。"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.trace import get_trace_id

TRACE_HEADER = "X-Trace-Id"


class ErrorCode:
    """稳定业务错误码，供前端做文案映射。"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    REFRESH_TOKEN_REUSED = "REFRESH_TOKEN_REUSED"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    RESUME_QUOTA_EXCEEDED = "RESUME_QUOTA_EXCEEDED"
    PARSE_FAILED = "PARSE_FAILED"
    RESUME_NOT_PARSED = "RESUME_NOT_PARSED"
    DICT_ITEM_EXISTS = "DICT_ITEM_EXISTS"
    FILE_PATH_INVALID = "FILE_PATH_INVALID"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_OUTPUT_INVALID = "MODEL_OUTPUT_INVALID"
    INTERVIEW_ALREADY_ONGOING = "INTERVIEW_ALREADY_ONGOING"
    INTERVIEW_NOT_ONGOING = "INTERVIEW_NOT_ONGOING"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """业务异常：携带 HTTP 状态码与稳定错误码。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def error_payload(
    code: str,
    message: str,
    trace_id: str | None,
    details: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": code,
        "message": message,
        "trace_id": trace_id,
    }
    if details is not None:
        payload["details"] = details
    return payload


def _respond(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    trace_id = get_trace_id() or getattr(request.state, "trace_id", None)
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code, message, trace_id, details),
        headers={TRACE_HEADER: trace_id} if trace_id else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _respond(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in err.get("loc", ())[1:]),
                "message": err.get("msg", ""),
            }
            for err in exc.errors()
        ]
        return _respond(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_ERROR,
            "请求参数校验失败",
            details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: ErrorCode.UNAUTHORIZED,
            404: ErrorCode.NOT_FOUND,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return _respond(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # 不向调用方泄露堆栈与内部实现细节
        return _respond(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_ERROR,
            "服务内部错误",
        )
