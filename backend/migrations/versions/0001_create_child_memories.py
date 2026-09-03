"""Create child memories table.

Revision ID: 0001
Revises:
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "child_memories",
        sa.Column("memory_id", sa.Uuid(), nullable=False),
        sa.Column("child_id", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("memory_id"),
    )
    op.create_index("idx_child_memories_child_id", "child_memories", ["child_id"])


def downgrade() -> None:
    op.drop_index("idx_child_memories_child_id", table_name="child_memories")
    op.drop_table("child_memories")
