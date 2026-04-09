"""System management service: categories and tags."""

from __future__ import annotations

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.system import (
    CategoryOutput,
    CategoryTreeOutput,
    CreateCategoryCommand,
    CreateTagCommand,
    ReorderTagsCommand,
    TagOutput,
    UpdateCategoryCommand,
    UpdateTagCommand,
)
from app.models.category import Category
from app.models.content import Content
from app.models.tag import Tag, content_tags
from app.services.system.errors import (
    CategoryHasChildrenError,
    CategoryHasContentsError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateTagError,
    TagInUseError,
    TagNotFoundError,
)

# ============================================================
# Category helpers
# ============================================================


def _category_to_output(cat: Category) -> CategoryOutput:
    return CategoryOutput(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        parent_id=cat.parent_id,
        sort_order=cat.sort_order,
        created_at=str(cat.created_at),
        updated_at=str(cat.updated_at),
    )


def _category_to_tree_output(
    cat: Category, *, include_children: bool = True
) -> CategoryTreeOutput:
    children = []
    if include_children:
        children = [
            _category_to_tree_output(c, include_children=False)
            for c in sorted(cat.children, key=lambda x: x.sort_order)
        ]
    return CategoryTreeOutput(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        parent_id=cat.parent_id,
        sort_order=cat.sort_order,
        children=children,
        created_at=str(cat.created_at),
        updated_at=str(cat.updated_at),
    )


# ============================================================
# Category CRUD
# ============================================================


async def list_categories_tree(db: AsyncSession) -> list[CategoryTreeOutput]:
    """List all categories as a tree (root nodes with children)."""
    result = await db.execute(
        select(Category)
        .where(Category.parent_id.is_(None))
        .options(selectinload(Category.children))
        .order_by(Category.sort_order, Category.id)
    )
    roots = result.unique().scalars().all()
    return [_category_to_tree_output(r) for r in roots]


async def get_category(db: AsyncSession, category_id: int) -> CategoryOutput:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise CategoryNotFoundError(category_id=category_id)
    return _category_to_output(cat)


async def create_category(
    db: AsyncSession,
    *,
    command: CreateCategoryCommand,
) -> CategoryOutput:
    # Check for duplicate name under same parent
    dup_filter = (
        Category.parent_id == command.parent_id
        if command.parent_id is not None
        else Category.parent_id.is_(None)
    )
    existing = await db.execute(
        select(Category).where(Category.name == command.name, dup_filter)
    )
    if existing.scalars().first() is not None:
        raise DuplicateCategoryError(name=command.name)

    # If parent_id is provided, verify parent exists
    if command.parent_id is not None:
        parent = await db.get(Category, command.parent_id)
        if parent is None:
            raise CategoryNotFoundError(category_id=command.parent_id)

    cat = Category(
        name=command.name,
        description=command.description,
        parent_id=command.parent_id,
        sort_order=command.sort_order,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return _category_to_output(cat)


async def update_category(
    db: AsyncSession,
    category_id: int,
    *,
    command: UpdateCategoryCommand,
) -> CategoryOutput:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise CategoryNotFoundError(category_id=category_id)

    if command.name is not None:
        dup_filter = (
            Category.parent_id == cat.parent_id
            if cat.parent_id is not None
            else Category.parent_id.is_(None)
        )
        existing = await db.execute(
            select(Category).where(
                Category.name == command.name,
                dup_filter,
                Category.id != category_id,
            )
        )
        if existing.scalars().first() is not None:
            raise DuplicateCategoryError(name=command.name)
        cat.name = command.name

    if command.description is not None:
        cat.description = command.description

    if command.sort_order is not None:
        cat.sort_order = command.sort_order

    await db.commit()
    await db.refresh(cat)
    return _category_to_output(cat)


async def delete_category(db: AsyncSession, category_id: int) -> None:
    cat = await db.get(Category, category_id)
    if cat is None:
        raise CategoryNotFoundError(category_id=category_id)

    # Check for children
    children_count = (
        await db.execute(
            select(func.count())
            .select_from(Category)
            .where(Category.parent_id == category_id)
        )
    ).scalar_one()
    if children_count > 0:
        raise CategoryHasChildrenError()

    # Check for contents using this category
    content_count = (
        await db.execute(
            select(func.count())
            .select_from(Content)
            .where(Content.category_id == category_id)
        )
    ).scalar_one()
    if content_count > 0:
        raise CategoryHasContentsError()

    await db.delete(cat)
    await db.commit()


# ============================================================
# Tag helpers
# ============================================================


def _tag_to_output(tag: Tag) -> TagOutput:
    return TagOutput(
        id=tag.id,
        name=tag.name,
        is_system=tag.is_system,
        sort_order=tag.sort_order,
        created_at=str(tag.created_at),
    )


# ============================================================
# Tag CRUD
# ============================================================


async def list_tags(db: AsyncSession) -> list[TagOutput]:
    """List all tags, system tags first (ordered by sort_order, then name)."""
    result = await db.execute(
        select(Tag).order_by(Tag.is_system.desc(), Tag.sort_order, Tag.name)
    )
    return [_tag_to_output(t) for t in result.scalars().all()]


async def get_tag(db: AsyncSession, tag_id: int) -> TagOutput:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise TagNotFoundError(tag_id=tag_id)
    return _tag_to_output(tag)


async def create_tag(
    db: AsyncSession,
    *,
    command: CreateTagCommand,
) -> TagOutput:
    existing = await db.execute(select(Tag).where(Tag.name == command.name))
    if existing.scalars().first() is not None:
        raise DuplicateTagError(name=command.name)

    tag = Tag(
        name=command.name, is_system=command.is_system, sort_order=command.sort_order
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return _tag_to_output(tag)


async def update_tag(
    db: AsyncSession,
    tag_id: int,
    *,
    command: UpdateTagCommand,
) -> TagOutput:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise TagNotFoundError(tag_id=tag_id)

    if command.name is not None:
        existing = await db.execute(
            select(Tag).where(Tag.name == command.name, Tag.id != tag_id)
        )
        if existing.scalars().first() is not None:
            raise DuplicateTagError(name=command.name)
        tag.name = command.name

    if command.is_system is not None:
        tag.is_system = command.is_system

    if command.sort_order is not None:
        tag.sort_order = command.sort_order

    await db.commit()
    await db.refresh(tag)
    return _tag_to_output(tag)


async def reorder_tags(
    db: AsyncSession, *, command: ReorderTagsCommand
) -> list[TagOutput]:
    """Batch-update sort_order for all tags in a single UPDATE statement."""
    if not command.items:
        return await list_tags(db)

    ids = [tag_id for tag_id, _ in command.items]

    # Verify all ids exist
    result = await db.execute(select(Tag.id).where(Tag.id.in_(ids)))
    found_ids = set(result.scalars().all())
    missing = set(ids) - found_ids
    if missing:
        raise TagNotFoundError(tag_id=next(iter(missing)))

    sort_case = case(
        dict(command.items),
        value=Tag.id,
    )
    await db.execute(update(Tag).where(Tag.id.in_(ids)).values(sort_order=sort_case))
    await db.commit()
    return await list_tags(db)


async def delete_tag(db: AsyncSession, tag_id: int) -> None:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise TagNotFoundError(tag_id=tag_id)

    # Check if tag is in use
    usage_count = (
        await db.execute(
            select(func.count())
            .select_from(content_tags)
            .where(content_tags.c.tag_id == tag_id)
        )
    ).scalar_one()
    if usage_count > 0:
        raise TagInUseError()

    await db.delete(tag)
    await db.commit()
