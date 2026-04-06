"""Admin routes: user management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.domains.content import UserRole
from app.models.user import User
from app.schemas.user import RoleUpdateIn, UserOut
from app.services.auth import (
    UserNotFoundError,
    list_users,
    raise_auth_error,
    update_user_role,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role(UserRole.admin)


@router.get("/users", response_model=list[UserOut])
async def list_users_route(
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    users = await list_users(db)
    return users


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role_route(
    user_id: int,
    body: RoleUpdateIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await update_user_role(db, user_id, body.role)
    if user is None:
        raise_auth_error(UserNotFoundError())
    return user
