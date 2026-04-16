from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class FeishuGroupChat(Base):
    __tablename__ = "feishu_group_chats"

    chat_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    chat_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
