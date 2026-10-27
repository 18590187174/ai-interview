"""迁移基线：可升级、可重复执行、可回滚。

默认在临时 SQLite 文件上验证；设置 TEST_DATABASE_URL 后可在真实数据库
（如本地 PostgreSQL）上验证同一套迁移。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "users",
    "refresh_tokens",
    "resumes",
    "knowledge_documents",
    "knowledge_chunks",
    "predictions",
    "predicted_questions",
    "app_settings",
    "interviews",
    "interview_messages",
    "alembic_version",
}
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _db_url(tmp_dir: Path | None) -> str:
    if TEST_DATABASE_URL:
        return TEST_DATABASE_URL
    target = (tmp_dir or Path(".")) / "migration.sqlite3"
    return f"sqlite+pysqlite:///{target.as_posix()}"


def _alembic_env(url: str) -> dict:
    env = dict(os.environ)
    env["DATABASE_URL"] = url
    env["JWT_SECRET_KEY"] = "test-secret-key"
    env["ENVIRONMENT"] = "test"
    return env


def _run_alembic(command: str, url: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", command, "head" if command == "upgrade" else "base"],
        cwd=str(BACKEND_DIR),
        env=_alembic_env(url),
        capture_output=True,
        text=True,
        check=False,
    )


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


@pytest.mark.slow
def test_upgrade_head_creates_schema(tmp_path):
    url = _db_url(tmp_path)
    result = _run_alembic("upgrade", url)
    assert result.returncode == 0, result.stdout + result.stderr
    assert EXPECTED_TABLES <= _tables(url)


@pytest.mark.slow
def test_upgrade_head_is_idempotent(tmp_path):
    url = _db_url(tmp_path)
    assert _run_alembic("upgrade", url).returncode == 0
    result = _run_alembic("upgrade", url)
    assert result.returncode == 0, result.stdout + result.stderr
    assert EXPECTED_TABLES <= _tables(url)


@pytest.mark.slow
def test_downgrade_base_removes_schema(tmp_path):
    url = _db_url(tmp_path)
    assert _run_alembic("upgrade", url).returncode == 0

    result = _run_alembic("downgrade", url)
    assert result.returncode == 0, result.stdout + result.stderr

    remaining = _tables(url)
    assert "users" not in remaining and "refresh_tokens" not in remaining


@pytest.mark.slow
def test_downgrade_only_drops_migration_owned_objects(tmp_path):
    """回滚只移除本次迁移引入的结构，不触碰其他对象。"""
    url = _db_url(tmp_path)
    marker = "unrelated_table"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS {marker} (id INTEGER PRIMARY KEY)"))
    engine.dispose()

    assert _run_alembic("upgrade", url).returncode == 0
    assert _run_alembic("downgrade", url).returncode == 0

    assert marker in _tables(url)
