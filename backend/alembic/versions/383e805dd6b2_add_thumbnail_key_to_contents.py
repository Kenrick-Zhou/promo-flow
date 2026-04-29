"""add thumbnail_key to contents

Revision ID: 383e805dd6b2
Revises: 20260418_0001
Create Date: 2026-04-29 23:07:48.268226

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "383e805dd6b2"
down_revision: str | None = "20260418_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contents",
        sa.Column("thumbnail_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contents", "thumbnail_key")
