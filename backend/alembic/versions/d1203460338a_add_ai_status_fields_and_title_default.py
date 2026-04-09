"""add_ai_status_fields_and_title_default

Revision ID: d1203460338a
Revises: c7959e0a81ca
Create Date: 2026-04-09 20:55:27.482979

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1203460338a"
down_revision: str | None = "c7959e0a81ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Backfill existing NULL titles before making the column NOT NULL
    op.execute("UPDATE contents SET title = '待AI生成' WHERE title IS NULL")
    op.alter_column(
        "contents",
        "title",
        existing_type=sa.VARCHAR(length=256),
        nullable=False,
        server_default="待AI生成",
    )

    op.add_column(
        "contents",
        sa.Column(
            "ai_status",
            sa.Enum(
                "pending",
                "processing",
                "completed",
                "failed",
                name="aistatus",
                native_enum=False,
            ),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("contents", sa.Column("ai_error", sa.Text(), nullable=True))
    op.add_column(
        "contents",
        sa.Column("ai_processed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contents", "ai_processed_at")
    op.drop_column("contents", "ai_error")
    op.drop_column("contents", "ai_status")
    op.alter_column(
        "contents",
        "title",
        existing_type=sa.VARCHAR(length=256),
        nullable=True,
        server_default=None,
    )
