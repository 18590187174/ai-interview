"""面试会话与问答消息模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interviews"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("predictions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # ongoing / completed / abandoned
    status: Mapped[str] = mapped_column(String(20), default="ongoing", index=True, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    current_position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_role: Mapped[str] = mapped_column(String(120), nullable=False)
    years_of_experience: Mapped[str] = mapped_column(String(40), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    programming_language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list[InterviewMessage]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.created_at",
    )


class InterviewMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_messages"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # interviewer（提问）/ answerer（回答或跳过）
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    interview: Mapped[Interview] = relationship(back_populates="messages")
