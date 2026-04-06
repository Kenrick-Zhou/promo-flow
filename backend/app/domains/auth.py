"""Auth domain types."""

from dataclasses import dataclass
from datetime import datetime

# ============================================================
# Command Objects
# ============================================================


@dataclass(slots=True)
class FeishuLoginCommand:
    """Command for Feishu OAuth login."""

    code: str


# ============================================================
# Output Objects
# ============================================================


@dataclass(slots=True)
class AuthSession:
    """Issued session after successful authentication."""

    access_token: str
    user_id: int
    user_name: str
    user_role: str
    avatar_url: str | None
    feishu_open_id: str
    created_at: datetime


@dataclass(slots=True)
class FeishuUserInfo:
    """User info fetched from Feishu."""

    open_id: str
    union_id: str
    name: str
    avatar_url: str | None
