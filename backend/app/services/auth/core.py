"""Feishu OAuth 2.0 authentication service."""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.domains.auth import AuthSession, FeishuLoginCommand, FeishuUserInfo
from app.domains.content import UserRole
from app.models.user import User
from app.services.auth.errors import FeishuOAuthError

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"


async def get_feishu_app_token() -> str:
    """Fetch tenant_access_token from Feishu."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.FEISHU_APP_ID,
                "app_secret": settings.FEISHU_APP_SECRET,
            },
        )
        resp.raise_for_status()
        token: str = resp.json()["tenant_access_token"]
        return token


async def _exchange_code_for_user_token(code: str) -> dict:
    """Exchange auth code for user_access_token."""
    app_token = await get_feishu_app_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{FEISHU_API_BASE}/authen/v1/oidc/access_token",
            headers={"Authorization": f"Bearer {app_token}"},
            json={"grant_type": "authorization_code", "code": code},
        )
        resp.raise_for_status()
        data: dict[str, object] = resp.json()["data"]
        return data


async def _get_feishu_user_info(user_access_token: str) -> FeishuUserInfo:
    """Fetch user info from Feishu using user access token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{FEISHU_API_BASE}/authen/v1/user_info",
            headers={"Authorization": f"Bearer {user_access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return FeishuUserInfo(
            open_id=data["open_id"],
            union_id=data.get("union_id", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url"),
        )


async def _get_or_create_user(db: AsyncSession, info: FeishuUserInfo) -> User:
    """Upsert user in database based on Feishu open_id."""
    stmt = select(User).where(User.feishu_open_id == info.open_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            feishu_open_id=info.open_id,
            feishu_union_id=info.union_id,
            name=info.name,
            avatar_url=info.avatar_url,
            role=UserRole.employee,
        )
        db.add(user)
    else:
        user.name = info.name
        user.avatar_url = info.avatar_url

    await db.commit()
    await db.refresh(user)
    return user


async def login_with_code(
    db: AsyncSession, *, command: FeishuLoginCommand
) -> AuthSession:
    """Full OAuth flow: code -> user info -> db upsert -> JWT."""
    try:
        token_data = await _exchange_code_for_user_token(command.code)
        user_info = await _get_feishu_user_info(token_data["access_token"])
    except (httpx.HTTPError, KeyError) as exc:
        raise FeishuOAuthError("Failed to authenticate with Feishu") from exc

    user = await _get_or_create_user(db, user_info)
    access_token = create_access_token(user.id)

    return AuthSession(
        access_token=access_token,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role.value,
        avatar_url=user.avatar_url,
        feishu_open_id=user.feishu_open_id,
        created_at=user.created_at,
    )


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch a user by ID."""
    return await db.get(User, user_id)


async def list_users(db: AsyncSession) -> list[User]:
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


async def update_user_role(
    db: AsyncSession, user_id: int, role: UserRole
) -> User | None:
    """Update a user's role."""
    user = await db.get(User, user_id)
    if user is None:
        return None
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user
