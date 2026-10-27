"""请求追踪中间件：生成或沿用追踪标识，并回显到响应头。"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.trace import TRACE_HEADER, bind_trace_id


class TraceIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(TRACE_HEADER)
        trace_id = bind_trace_id(incoming)
        request.state.trace_id = trace_id
        try:
            response = await call_next(request)
        finally:
            pass
        response.headers[TRACE_HEADER] = trace_id
        return response
