"""请求追踪标识：在日志与响应中贯穿同一次请求。"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

TRACE_HEADER = "X-Trace-Id"

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def bind_trace_id(trace_id: str | None = None) -> str:
    value = trace_id or uuid.uuid4().hex
    _trace_id.set(value)
    return value


def get_trace_id() -> str | None:
    return _trace_id.get()


def reset_trace_id(token: object | None = None) -> None:
    _trace_id.set(None)
