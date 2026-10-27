"""字典项请求与响应结构。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DictItemCreate(BaseModel):
    type: str = Field(min_length=1, max_length=40, description="字典类型")
    label: str = Field(min_length=1, max_length=80, description="显示名称")
    value: str | None = Field(default=None, max_length=80, description="存储值，缺省同 label")
    sort_order: int = Field(default=0, description="排序权重，越小越靠前")


class DictItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    label: str
    value: str
    sort_order: int
    enabled: bool
    created_at: datetime
