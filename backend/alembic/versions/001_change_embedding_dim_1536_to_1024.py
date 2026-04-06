"""change embedding dim from 1536 to 1024

Revision ID: 001
Revises:
Create Date: 2026-04-06

Switch from OpenAI text-embedding-3-small (1536) to
DashScope text-embedding-v3 (1024).
Existing embedding data is dropped as the dimension is incompatible.
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing embedding column (dimension incompatible) and recreate at 1024
    op.execute("ALTER TABLE contents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE contents ADD COLUMN embedding vector(1024)")


def downgrade() -> None:
    op.execute("ALTER TABLE contents DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE contents ADD COLUMN embedding vector(1536)")
