"""add_media_width_height_to_contents

Revision ID: 7ea4adb99f96
Revises: d1203460338a
Create Date: 2026-04-13 17:23:11.104239

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ea4adb99f96"
down_revision: str | None = "d1203460338a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contents", sa.Column("media_width", sa.Integer(), nullable=True))
    op.add_column("contents", sa.Column("media_height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("contents", "media_height")
    op.drop_column("contents", "media_width")
