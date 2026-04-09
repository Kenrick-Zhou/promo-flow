"""make_content_title_nullable

Revision ID: 7d9e61b5d4b3
Revises: fb0ec359f088
Create Date: 2026-04-09 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d9e61b5d4b3"
down_revision: str | None = "fb0ec359f088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "contents",
        "title",
        existing_type=sa.String(length=256),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "contents",
        "title",
        existing_type=sa.String(length=256),
        nullable=False,
    )
