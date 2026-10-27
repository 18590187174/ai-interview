"""运行时系统设置：键值存取与 LLM 凭据解析（数据库覆盖 > 环境变量）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.system_setting import SystemSetting

KEY_LLM_API_KEY = "llm_api_key"
KEY_LLM_BASE_URL = "llm_base_url"
KEY_LLM_MODEL = "llm_model"

_URL_PATTERN = re.compile(r"^https?://\S+$")


def get_value(db: Session, key: str) -> str | None:
    row = db.get(SystemSetting, key)
    return row.value if row is not None else None


def set_value(db: Session, key: str, value: str) -> None:
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def delete_value(db: Session, key: str) -> None:
    row = db.get(SystemSetting, key)
    if row is not None:
        db.delete(row)
        db.commit()


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 4:
        return "***"
    return f"***{api_key[-4:]}"


@dataclass(frozen=True)
class LLMRuntimeConfig:
    """押题调用大模型时实际使用的运行时凭据。"""

    api_key: str | None
    base_url: str
    model: str
    source: str  # database / environment / none


def effective_llm_config(db: Session, settings: Settings) -> LLMRuntimeConfig:
    db_key = get_value(db, KEY_LLM_API_KEY)
    db_base_url = get_value(db, KEY_LLM_BASE_URL)
    db_model = get_value(db, KEY_LLM_MODEL)

    if db_key:
        source = "database"
    elif settings.llm_api_key:
        source = "environment"
    else:
        source = "none"

    return LLMRuntimeConfig(
        api_key=db_key or settings.llm_api_key,
        base_url=db_base_url or settings.llm_base_url,
        model=db_model or settings.llm_model,
        source=source,
    )


def llm_status(db: Session, settings: Settings) -> dict:
    db_key = get_value(db, KEY_LLM_API_KEY)
    config = effective_llm_config(db, settings)
    return {
        "has_api_key": bool(config.api_key),
        "api_key_masked": mask_api_key(db_key) if db_key else None,
        "base_url": config.base_url,
        "model": config.model,
        "source": config.source,
    }
