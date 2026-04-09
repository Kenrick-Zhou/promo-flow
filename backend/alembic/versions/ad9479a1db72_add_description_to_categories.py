"""add_description_to_categories

Revision ID: ad9479a1db72
Revises: fb0ec359f088
Create Date: 2026-04-08 21:20:26.932087

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad9479a1db72"
down_revision: str | None = "fb0ec359f088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column(
            "description", sa.String(length=256), server_default="", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("categories", "description")
