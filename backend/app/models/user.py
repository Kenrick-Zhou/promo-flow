from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.domains.content import UserRole

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.content import Content


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feishu_open_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    feishu_union_id: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False, default=UserRole.employee
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contents: Mapped[list["Content"]] = relationship(
        "Content", back_populates="uploader"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="auditor"
    )
