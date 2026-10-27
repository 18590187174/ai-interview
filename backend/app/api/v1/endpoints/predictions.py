"""押题端点。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.prediction import (
    PredictionCreate,
    PredictionOut,
    PredictionSummaryOut,
)
from app.services import prediction as prediction_service
from app.services.llm import LLMClient, OpenAICompatLLM

router = APIRouter(prefix="/predictions", tags=["predictions"])


def get_llm() -> LLMClient:
    """大模型客户端依赖：测试可注入桩实现。"""
    return OpenAICompatLLM()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PredictionOut)
def create_prediction(
    payload: PredictionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    llm: LLMClient = Depends(get_llm),
) -> PredictionOut:
    prediction = prediction_service.create_prediction(
        db,
        user=user,
        resume_id=payload.resume_id,
        target_role=payload.target_role.strip(),
        years_of_experience=payload.years_of_experience.strip(),
        job_description=payload.job_description.strip(),
        programming_language=(payload.programming_language or "").strip() or None,
        settings=settings,
        llm=llm,
    )
    return PredictionOut.model_validate(prediction)


@router.get("", response_model=list[PredictionSummaryOut])
def list_predictions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PredictionSummaryOut]:
    predictions = prediction_service.list_predictions(db, user.id)
    return [
        PredictionSummaryOut(
            id=item.id,
            target_role=item.target_role,
            years_of_experience=item.years_of_experience,
            model_name=item.model_name,
            prompt_version=item.prompt_version,
            generated_at=item.generated_at,
            question_count=len(item.questions),
        )
        for item in predictions
    ]


@router.get("/{prediction_id}", response_model=PredictionOut)
def get_prediction(
    prediction_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionOut:
    prediction = prediction_service.get_owned_prediction(db, user.id, prediction_id)
    return PredictionOut.model_validate(prediction)
