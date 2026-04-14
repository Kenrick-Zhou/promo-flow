"""add_search_document_embedding_text_to_contents

Revision ID: 56c2acf66c24
Revises: 2f3b7269c43a
Create Date: 2026-04-13 20:54:35.454687

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "56c2acf66c24"
down_revision: str | None = "2f3b7269c43a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contents", sa.Column("search_document", sa.Text(), nullable=True))
    op.add_column("contents", sa.Column("embedding_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("contents", "embedding_text")
    op.drop_column("contents", "search_document")
