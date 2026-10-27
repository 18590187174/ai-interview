"""字典项模型：可配置的下拉选项（目标岗位、编程语言等）。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DictItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dict_items"
    __table_args__ = (UniqueConstraint("type", "value", name="uq_dict_items_type_value"),)

    # 字典类型：target_role / programming_language
    type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
