"""add approved_at to contents

Revision ID: 0f6919d91c76
Revises: 383e805dd6b2
Create Date: 2026-04-29 23:37:39.670072

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f6919d91c76"
down_revision: str | None = "383e805dd6b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contents",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill: for already-approved content, use updated_at as a best-effort
    # approximation of the original approval time so the marketplace can sort
    # by approval time without leaving these items at the bottom.
    op.execute(
        "UPDATE contents SET approved_at = updated_at "
        "WHERE status = 'approved' AND approved_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("contents", "approved_at")
