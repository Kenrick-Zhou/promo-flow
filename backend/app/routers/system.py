"""Public system configuration endpoints (categories, tags)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.system import CategoryTreeOut, TagOut
from app.services.system import list_categories_tree, list_tags

router = APIRouter(tags=["system"])


@router.get(
    "/categories",
    response_model=list[CategoryTreeOut],
    summary="获取类目树",
    description="返回所有一级类目及其级联的二级类目。所有已认证用户均可访问。",
)
async def list_categories_route(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CategoryTreeOut]:
    categories = await list_categories_tree(db)
    return [CategoryTreeOut.from_domain(c) for c in categories]


@router.get(
    "/tags",
    response_model=list[TagOut],
    summary="获取标签列表",
    description="返回所有标签（系统默认标签优先显示）。所有已认证用户均可访问。",
)
async def list_tags_route(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TagOut]:
    tags = await list_tags(db)
    return [TagOut.from_domain(t) for t in tags]
