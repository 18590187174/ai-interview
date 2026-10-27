"""知识库文档相关响应结构。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class KnowledgeDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    size_bytes: int
    content_type: str
    is_public: bool
    retrievable: bool
    parse_error: str | None = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def parse_error_code(self) -> str | None:
        return "PARSE_FAILED" if self.parse_error else None
