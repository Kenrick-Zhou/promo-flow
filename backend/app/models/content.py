from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.domains.content import AiStatus, ContentStatus, ContentType
from app.models.tag import content_tags

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.category import Category
    from app.models.tag import Tag
    from app.models.user import User

EMBEDDING_DIM = 1024  # DashScope text-embedding-v3


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="待AI生成")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, native_enum=False), nullable=False
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, native_enum=False),
        nullable=False,
        default=ContentStatus.pending,
    )

    # File info (stored in OSS)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)  # OSS object key
    file_url: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )  # public URL if any
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)  # bytes
    media_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI generated fields
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    embedding: Mapped[list | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    ai_status: Mapped[AiStatus] = mapped_column(
        Enum(AiStatus, native_enum=False),
        nullable=False,
        default=AiStatus.pending,
    )
    ai_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Category (secondary/leaf category)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )

    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    uploader: Mapped["User"] = relationship("User", back_populates="contents")
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="content", cascade="all, delete-orphan"
    )
    category: Mapped["Category | None"] = relationship("Category")
    tag_objects: Mapped[list["Tag"]] = relationship("Tag", secondary=content_tags)
