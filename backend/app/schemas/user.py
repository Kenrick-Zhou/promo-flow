from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domains.auth import AuthSession
from app.domains.content import UserRole


class UserOut(BaseModel):
    id: int
    name: str
    avatar_url: str | None = None
    role: UserRole
    feishu_open_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

    @classmethod
    def from_domain(cls, session: AuthSession) -> TokenOut:
        """Construct HTTP response from domain AuthSession."""
        return cls(
            access_token=session.access_token,
            user=UserOut(
                id=session.user_id,
                name=session.user_name,
                role=UserRole(session.user_role),
                avatar_url=session.avatar_url,
                feishu_open_id=session.feishu_open_id,
                created_at=session.created_at,
            ),
        )


class RoleUpdateIn(BaseModel):
    role: UserRole
