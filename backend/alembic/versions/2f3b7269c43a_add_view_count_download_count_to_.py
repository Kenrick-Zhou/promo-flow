"""add_view_count_download_count_to_contents

Revision ID: 2f3b7269c43a
Revises: 7ea4adb99f96
Create Date: 2026-04-13 18:08:26.300837

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f3b7269c43a"
down_revision: str | None = "7ea4adb99f96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contents",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contents",
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("contents", "download_count")
    op.drop_column("contents", "view_count")
