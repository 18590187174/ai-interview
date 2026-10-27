"""押题相关请求与响应结构。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionCreate(BaseModel):
    resume_id: uuid.UUID
    target_role: str = Field(min_length=1, max_length=120, description="目标岗位")
    years_of_experience: str = Field(min_length=1, max_length=40, description="工作年限")
    job_description: str = Field(min_length=1, max_length=2000, description="岗位描述")
    programming_language: str | None = Field(
        default=None, max_length=40, description="编程语言（可选）"
    )


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    ref: str
    ref_id: str | None = None
    excerpt: str


class PredictedQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    question: str
    difficulty: str
    reference_answer: str | None = None
    evidence: list[EvidenceOut]


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    target_role: str
    years_of_experience: str
    job_description: str
    programming_language: str | None
    model_name: str
    prompt_version: str
    generated_at: datetime
    questions: list[PredictedQuestionOut]


class PredictionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_role: str
    years_of_experience: str
    model_name: str
    prompt_version: str
    generated_at: datetime
    question_count: int
