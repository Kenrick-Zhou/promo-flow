"""Admin routes: user management, category/tag management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.domains.content import UserRole
from app.models.user import User
from app.schemas.system import (
    CategoryCreateIn,
    CategoryOut,
    CategoryUpdateIn,
    TagCreateIn,
    TagOut,
    TagReorderIn,
    TagUpdateIn,
)
from app.schemas.user import RoleUpdateIn, UserOut
from app.services.auth import (
    UserNotFoundError,
    list_users,
    raise_auth_error,
    update_user_role,
)
from app.services.system import (
    CategoryHasChildrenError,
    CategoryHasContentsError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateTagError,
    TagInUseError,
    TagNotFoundError,
    create_category,
    create_tag,
    delete_category,
    delete_tag,
    raise_system_error,
    reorder_tags,
    update_category,
    update_tag,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_only = require_role(UserRole.admin)


# ============================================================
# User Management
# ============================================================


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


# ============================================================
# Category Management
# ============================================================


@router.post(
    "/categories",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建类目",
    description="创建一级类目（不传 parent_id）或二级类目（传 parent_id 指向父类目）。",
)
async def create_category_route(
    data: CategoryCreateIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryOut:
    try:
        output = await create_category(db, command=data.to_domain())
    except (CategoryNotFoundError, DuplicateCategoryError) as exc:
        raise_system_error(exc)
    return CategoryOut.from_domain(output)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryOut,
    summary="更新类目",
)
async def update_category_route(
    category_id: int,
    data: CategoryUpdateIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategoryOut:
    try:
        output = await update_category(db, category_id, command=data.to_domain())
    except (CategoryNotFoundError, DuplicateCategoryError) as exc:
        raise_system_error(exc)
    return CategoryOut.from_domain(output)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除类目",
    description="删除一个类目。如果类目下有子类目或素材，则无法删除。",
)
async def delete_category_route(
    category_id: int,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await delete_category(db, category_id)
    except (
        CategoryNotFoundError,
        CategoryHasChildrenError,
        CategoryHasContentsError,
    ) as exc:
        raise_system_error(exc)


# ============================================================
# Tag Management
# ============================================================


@router.post(
    "/tags",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建标签",
    description="创建系统默认标签或普通标签。",
)
async def create_tag_route(
    data: TagCreateIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TagOut:
    try:
        output = await create_tag(db, command=data.to_domain())
    except DuplicateTagError as exc:
        raise_system_error(exc)
    return TagOut.from_domain(output)


@router.patch(
    "/tags/{tag_id}",
    response_model=TagOut,
    summary="更新标签",
)
async def update_tag_route(
    tag_id: int,
    data: TagUpdateIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TagOut:
    try:
        output = await update_tag(db, tag_id, command=data.to_domain())
    except (TagNotFoundError, DuplicateTagError) as exc:
        raise_system_error(exc)
    return TagOut.from_domain(output)


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除标签",
    description="删除一个标签。如果标签正在被素材使用，则无法删除。",
)
async def delete_tag_route(
    tag_id: int,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await delete_tag(db, tag_id)
    except (TagNotFoundError, TagInUseError) as exc:
        raise_system_error(exc)


@router.put(
    "/tags/reorder",
    response_model=list[TagOut],
    summary="批量调整系统标签顺序",
    description="传入标签 id 与目标 sort_order 的列表，批量更新顺序。",
)
async def reorder_tags_route(
    data: TagReorderIn,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TagOut]:
    try:
        tags = await reorder_tags(db, command=data.to_domain())
    except TagNotFoundError as exc:
        raise_system_error(exc)
    return [TagOut.from_domain(t) for t in tags]
