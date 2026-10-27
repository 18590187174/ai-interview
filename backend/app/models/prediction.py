"""押题记录与押题题目模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Prediction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "predictions"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_role: Mapped[str] = mapped_column(String(120), nullable=False)
    years_of_experience: Mapped[str] = mapped_column(String(40), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    programming_language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    questions: Mapped[list[PredictedQuestion]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
        order_by="PredictedQuestion.position",
    )


class PredictedQuestion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "predicted_questions"

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("predictions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 命中依据：[{"source": "resume"|"job_description"|"knowledge", "ref": str, "excerpt": str}]
    evidence: Mapped[list] = mapped_column(JSON, nullable=False)

    prediction: Mapped[Prediction] = relationship(back_populates="questions")
