"""面试会话请求与响应结构。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class InterviewCreate(BaseModel):
    prediction_id: uuid.UUID


class AnswerCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000, description="回答内容")

    @field_validator("content")
    @classmethod
    def content_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("回答内容不能为空")
        return stripped


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    position: int
    content: str | None
    skipped: bool
    created_at: datetime


class QuestionOut(BaseModel):
    position: int
    question: str
    difficulty: str
    reference_answer: str | None = None


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    prediction_id: uuid.UUID
    total_questions: int
    current_position: int
    target_role: str
    years_of_experience: str
    programming_language: str | None
    # 模型无独立 started_at 列，开始时间即 created_at
    started_at: datetime = Field(validation_alias=AliasChoices("started_at", "created_at"))
    finished_at: datetime | None
    messages: list[MessageOut]


class InterviewSummaryOut(BaseModel):
    id: uuid.UUID
    status: str
    target_role: str
    total_questions: int
    current_position: int
    started_at: datetime
    finished_at: datetime | None
    answered_count: int


# 兼容说明：Interview 模型无独立 started_at 列，开始时间即 created_at


class InterviewStartOut(BaseModel):
    """发起面试：会话信息 + 题目列表 + 当前进度。"""

    interview: InterviewOut
    questions: list[QuestionOut]


class AnswerResultOut(BaseModel):
    """提交回答/跳过后的结果：推进到下一题或完成标记。"""

    interview: InterviewOut
    questions: list[QuestionOut]
    finished: bool
