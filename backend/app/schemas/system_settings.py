"""系统设置请求与响应结构。"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class LLMSettingsUpdate(BaseModel):
    """api_key/base_url/model 传 None 表示不修改，传空串表示清除并回落默认。"""

    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if stripped and not stripped.startswith(("http://", "https://")):
            raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
        return stripped or None

    @field_validator("model", "api_key")
    @classmethod
    def strip_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class LLMSettingsOut(BaseModel):
    has_api_key: bool
    api_key_masked: str | None = None
    base_url: str
    model: str
    source: str  # database / environment / none


class LLMSettingsSaveOut(BaseModel):
    has_api_key: bool
    api_key_masked: str | None = None
    message: str
