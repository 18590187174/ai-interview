"""系统设置端点：LLM 凭据的查询与更新（凭据永不回显完整明文）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import AppError, ErrorCode
from app.models.user import User
from app.schemas.system_settings import LLMSettingsOut, LLMSettingsSaveOut, LLMSettingsUpdate
from app.services import system_settings as settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/llm", response_model=LLMSettingsOut)
def get_llm_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LLMSettingsOut:
    status = settings_service.llm_status(db, settings)
    return LLMSettingsOut(**status)


@router.put("/llm", response_model=LLMSettingsSaveOut)
def update_llm_settings(
    payload: LLMSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LLMSettingsSaveOut:
    if payload.api_key is not None:
        if payload.api_key == "":
            settings_service.delete_value(db, settings_service.KEY_LLM_API_KEY)
        else:
            settings_service.set_value(db, settings_service.KEY_LLM_API_KEY, payload.api_key)

    if payload.base_url is not None:
        if payload.base_url == "":
            settings_service.delete_value(db, settings_service.KEY_LLM_BASE_URL)
        else:
            if not settings_service._URL_PATTERN.match(payload.base_url):
                raise AppError(
                    422,
                    ErrorCode.VALIDATION_ERROR,
                    "Base URL 必须以 http:// 或 https:// 开头",
                )
            settings_service.set_value(db, settings_service.KEY_LLM_BASE_URL, payload.base_url)

    if payload.model is not None:
        if payload.model == "":
            settings_service.delete_value(db, settings_service.KEY_LLM_MODEL)
        else:
            settings_service.set_value(db, settings_service.KEY_LLM_MODEL, payload.model)

    status = settings_service.llm_status(db, settings)
    return LLMSettingsSaveOut(
        has_api_key=status["has_api_key"],
        api_key_masked=status["api_key_masked"],
        message="保存成功，押题将立即使用新配置",
    )
