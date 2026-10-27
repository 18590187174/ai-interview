"""测试夹具：默认使用内存 SQLite 隔离每个用例。

设置 TEST_DATABASE_URL 可切换为其他数据库（如本地 PostgreSQL），
用于在真实方言上验证模型与查询的兼容性。
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# 必须在导入应用之前设置环境变量
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

DEFAULT_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    test_engine = create_engine(url, **kwargs)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    # 清理表结构，避免共享数据库（如真实 PostgreSQL）时影响迁移测试
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(engine) -> Iterator[Session]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    # 关闭异常重抛，以便验证统一错误响应格式（而非让测试框架抛出服务端异常）
    raise_mode = os.environ.get("RAISE_SERVER_EXCEPTIONS", "0") == "1"
    with TestClient(app, raise_server_exceptions=raise_mode) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_user(client) -> dict:
    """注册一个用户并返回其邮箱、密码与用户 ID。"""
    email = f"user-{os.urandom(4).hex()}@example.com"
    password = "Passw0rd1"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert response.status_code == 201, response.text
    return {"email": email, "password": password, "id": response.json()["id"]}
