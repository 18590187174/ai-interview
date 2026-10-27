"""add reference_answer to predicted_questions

Revision ID: b7e2f9a4c8d1
Revises: f2430d02b06e
Create Date: 2026-10-26

押题题目新增参考答案字段（可空，兼容历史记录）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2f9a4c8d1"
down_revision: str | None = "f2430d02b06e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "predicted_questions",
        sa.Column("reference_answer", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("predicted_questions", "reference_answer")
