"""merge_heads

Revision ID: c7959e0a81ca
Revises: 7d9e61b5d4b3, ad9479a1db72
Create Date: 2026-04-09 20:54:36.935441

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7959e0a81ca"
down_revision: str | None = ("7d9e61b5d4b3", "ad9479a1db72")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
