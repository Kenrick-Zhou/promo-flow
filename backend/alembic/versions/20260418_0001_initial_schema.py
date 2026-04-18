"""initial schema

Revision ID: 20260418_0001
Revises:
Create Date: 2026-04-18 00:00:00.000000

Baseline migration for the current PromoFlow schema.
This replaces the previously broken/incomplete migration chain before the
first production deployment.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260418_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "description",
            sa.String(length=256),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_category_name_parent",
        "categories",
        ["name", "parent_id"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )
    op.create_index(
        "ix_category_name_root",
        "categories",
        ["name"],
        unique=True,
        postgresql_where=sa.text("parent_id IS NULL"),
    )

    op.create_table(
        "feishu_group_chats",
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("chat_name", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("chat_id"),
    )

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("feishu_open_id", sa.String(length=128), nullable=False),
        sa.Column("feishu_union_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "employee",
                "reviewer",
                "admin",
                name="userrole",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feishu_union_id"),
    )
    op.create_index(
        op.f("ix_users_feishu_open_id"),
        "users",
        ["feishu_open_id"],
        unique=True,
    )

    op.create_table(
        "contents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "content_type",
            sa.Enum("image", "video", name="contenttype", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="contentstatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(length=512), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("media_width", sa.Integer(), nullable=True),
        sa.Column("media_height", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False),
        sa.Column("download_count", sa.Integer(), nullable=False),
        sa.Column("hot_score", sa.Float(), nullable=False),
        sa.Column("hot_score_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column(
            "ai_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("embedding", Vector(dim=1024), nullable=True),
        sa.Column(
            "ai_status",
            sa.Enum(
                "pending",
                "processing",
                "completed",
                "failed",
                name="aistatus",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("ai_error", sa.Text(), nullable=True),
        sa.Column("ai_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("search_document", sa.Text(), nullable=True),
        sa.Column("embedding_text", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contents_hot_score"),
        "contents",
        ["hot_score"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("auditor_id", sa.Integer(), nullable=False),
        sa.Column("audit_status", sa.String(length=32), nullable=False),
        sa.Column("audit_comments", sa.Text(), nullable=True),
        sa.Column(
            "audit_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["auditor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_content_id"),
        "audit_logs",
        ["content_id"],
        unique=False,
    )

    op.create_table(
        "content_tags",
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("content_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("content_tags")

    op.drop_index(op.f("ix_audit_logs_content_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_contents_hot_score"), table_name="contents")
    op.drop_table("contents")

    op.drop_index(op.f("ix_users_feishu_open_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")

    op.drop_table("feishu_group_chats")

    op.drop_index(
        "ix_category_name_root",
        table_name="categories",
        postgresql_where=sa.text("parent_id IS NULL"),
    )
    op.drop_index(
        "ix_category_name_parent",
        table_name="categories",
        postgresql_where=sa.text("parent_id IS NOT NULL"),
    )
    op.drop_table("categories")
