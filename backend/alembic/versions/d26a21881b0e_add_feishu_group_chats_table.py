"""add_feishu_group_chats_table

Revision ID: d26a21881b0e
Revises: 28a9a56a4a6d
Create Date: 2026-04-16 20:34:58.973299

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d26a21881b0e"
down_revision: str | None = "28a9a56a4a6d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feishu_group_chats",
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("chat_name", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("chat_id"),
    )


def downgrade() -> None:
    op.drop_table("feishu_group_chats")
