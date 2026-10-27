"""平台基础：健康检查、统一错误格式、请求追踪、默认拒绝、配置校验。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.core.errors import ErrorCode
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]
TRACE_HEADER = "X-Trace-Id"


class TestHealth:
    def test_health_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "ok"
        assert body["trace_id"]

    def test_health_degraded_when_database_unavailable(self, client):
        class BrokenSession:
            def execute(self, *args, **kwargs):
                raise SQLAlchemyError("database down")

        def broken_db():
            yield BrokenSession()

        app.dependency_overrides[get_db] = broken_db
        try:
            response = client.get("/api/v1/health")
        finally:
            app.dependency_overrides.pop(get_db, None)

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "degraded"
        assert body["database"] == "unavailable"


class TestErrorFormat:
    def test_validation_error_returns_unified_payload(self, client):
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422
        body = response.json()
        assert body["code"] == ErrorCode.VALIDATION_ERROR
        assert "message" in body and body["trace_id"]
        assert isinstance(body["details"], list)

    def test_not_found_returns_unified_payload(self, client):
        response = client.get("/api/v1/does-not-exist")
        assert response.status_code == 404
        assert response.json()["code"] == ErrorCode.NOT_FOUND

    def test_unexpected_error_hides_internal_details(self, client, registered_user):
        def boom():
            raise RuntimeError("数据库连接串 postgres://user:password@host/db")

        app.add_api_route("/_boom", boom, methods=["GET"], include_in_schema=False)
        try:
            response = client.get("/_boom")
        finally:
            boom_route = next(
                (r for r in app.routes if getattr(r, "path", "") == "/_boom"), None
            )
            if boom_route is not None:
                app.router.routes.remove(boom_route)

        assert response.status_code == 500
        body = response.json()
        assert body["code"] == ErrorCode.INTERNAL_ERROR
        assert "password" not in response.text
        assert "Traceback" not in response.text


class TestTraceId:
    def test_each_request_gets_its_own_trace_id(self, client):
        first = client.get("/api/v1/health")
        second = client.get("/api/v1/health")
        assert first.headers[TRACE_HEADER] != second.headers[TRACE_HEADER]
        assert first.json()["trace_id"] == first.headers[TRACE_HEADER]

    def test_upstream_trace_id_is_preserved(self, client):
        upstream = "upstream-trace-123"
        response = client.get("/api/v1/health", headers={TRACE_HEADER: upstream})
        assert response.headers[TRACE_HEADER] == upstream
        assert response.json()["trace_id"] == upstream


class TestProtectedByDefault:
    def test_missing_token_is_rejected(self, client):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401
        assert response.json()["code"] == ErrorCode.UNAUTHORIZED

    def test_invalid_token_is_rejected(self, client):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401
        assert response.json()["code"] == ErrorCode.TOKEN_INVALID


class TestConfiguration:
    def test_missing_required_setting_fails_with_name(self):
        env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET_KEY"}
        env["DATABASE_URL"] = "sqlite+pysqlite:///./tmp-config-check.db"
        result = subprocess.run(
            [sys.executable, "-c", "from app.main import create_app; create_app()"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "JWT_SECRET_KEY" in (result.stdout + result.stderr)


@pytest.mark.parametrize("route", ["/api/v1/health", "/api/v1/auth/login"])
def test_public_routes_do_not_require_token(client, route):
    response = client.get(route)
    assert response.status_code != 401


def test_protected_route_dependency_is_declared():
    """受保护路由组必须声明认证依赖，确保新增接口默认拒绝。"""
    from app.api.v1.router import protected_router

    assert protected_router.dependencies, "受保护路由缺少认证依赖"
