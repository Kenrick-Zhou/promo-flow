"""add_hot_score_to_contents

Revision ID: 28a9a56a4a6d
Revises: 56c2acf66c24
Create Date: 2026-04-16 15:31:24.746037

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "28a9a56a4a6d"
down_revision: str | None = "56c2acf66c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contents",
        sa.Column("hot_score", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contents",
        sa.Column("hot_score_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_contents_hot_score"), "contents", ["hot_score"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_contents_hot_score"), table_name="contents")
    op.drop_column("contents", "hot_score_updated_at")
    op.drop_column("contents", "hot_score")
