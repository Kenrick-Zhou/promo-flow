"""add_sort_order_to_tags

Revision ID: fb0ec359f088
Revises: 1adcba406cef
Create Date: 2026-04-08 16:03:35.922580

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fb0ec359f088"
down_revision: str | None = "1adcba406cef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tags",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("tags", "sort_order")
