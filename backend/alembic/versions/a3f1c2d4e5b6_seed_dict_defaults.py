"""seed dict defaults

Revision ID: a3f1c2d4e5b6
Revises: 11a99ce2b536
Create Date: 2026-10-26

预置默认的目标岗位与编程语言字典项：
- 逐项检查存在性后再插入，不覆盖用户已配置的项
- 重复执行幂等
"""

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
import uuid
from alembic import op

revision: str = "a3f1c2d4e5b6"
down_revision: str | None = "11a99ce2b536"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_ITEMS: list[dict] = [
    {"type": "target_role", "label": label, "value": label, "sort_order": index}
    for index, label in enumerate(
        [
            "前端工程师",
            "后端工程师",
            "全栈工程师",
            "算法工程师",
            "测试工程师",
            "数据分析师",
            "产品经理",
        ]
    )
] + [
    {"type": "programming_language", "label": label, "value": label, "sort_order": index}
    for index, label in enumerate(
        ["Python", "Java", "JavaScript/TypeScript", "Go", "C++", "C#", "其他"]
    )
]

dict_items_table = sa.table(
    "dict_items",
    sa.column("id", sa.Uuid),
    sa.column("type", sa.String),
    sa.column("label", sa.String),
    sa.column("value", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("enabled", sa.Boolean),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _seed_rows(now: datetime) -> list[dict]:
    return [
        {
            "id": uuid.uuid4(),
            "type": item["type"],
            "label": item["label"],
            "value": item["value"],
            "sort_order": item["sort_order"],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        }
        for item in SEED_ITEMS
    ]


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        (row[0], row[1]) for row in conn.execute(sa.text("SELECT type, value FROM dict_items"))
    }
    now = datetime.now(timezone.utc)
    pending = [row for row in _seed_rows(now) if (row["type"], row["value"]) not in existing]
    if pending:
        op.bulk_insert(dict_items_table, pending)


def downgrade() -> None:
    seeds = {(item["type"], item["value"]) for item in SEED_ITEMS}
    conn = op.get_bind()
    for row in conn.execute(sa.text("SELECT id, type, value FROM dict_items")).fetchall():
        if (row[1], row[2]) in seeds:
            conn.execute(sa.text("DELETE FROM dict_items WHERE id = :id"), {"id": row[0]})
