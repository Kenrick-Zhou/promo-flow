from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        ForeignKey("contents.id"), nullable=False, index=True
    )
    auditor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    audit_status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # approved / rejected
    audit_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    content: Mapped["Content"] = relationship("Content", back_populates="audit_logs")
    auditor: Mapped["User"] = relationship("User", back_populates="audit_logs")
