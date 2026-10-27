"""新增配置项的默认值与派生值测试。"""

from __future__ import annotations

import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(JWT_SECRET_KEY="test-secret-key")  # type: ignore[call-arg]


def test_llm_defaults(settings: Settings) -> None:
    assert settings.llm_api_key is None
    assert settings.llm_base_url == "https://api.deepseek.com/v1"
    assert settings.llm_model == "deepseek-chat"
    assert settings.llm_timeout_seconds == 120
    assert settings.prompt_version == "prediction-v1"
    assert settings.prediction_question_count == 8


def test_upload_defaults(settings: Settings) -> None:
    assert settings.upload_max_size_mb == 10
    assert settings.upload_max_size_bytes == 10 * 1024 * 1024
    assert settings.resume_quota_per_user == 10
    assert settings.resume_max_chars == 12000
    assert settings.upload_root == "var/uploads"


def test_llm_key_can_be_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "deepseek-reasoner")
    settings = Settings(JWT_SECRET_KEY="test-secret-key")  # type: ignore[call-arg]
    assert settings.llm_api_key == "sk-test"
    assert settings.llm_model == "deepseek-reasoner"
