"""Semantic search service using pgvector cosine similarity."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    SearchContentCommand,
    SearchResultOutput,
)
from app.models.category import Category
from app.models.content import Content


def _content_to_output(content: Content) -> ContentOutput:
    """Convert ORM Content to domain output."""
    category: Category | None = content.category  # type: ignore[assignment]
    return ContentOutput(
        id=content.id,
        title=content.title,
        description=content.description,
        tags=[t.name for t in content.tag_objects],
        content_type=ContentType(content.content_type),
        status=ContentStatus(content.status),
        file_key=content.file_key,
        file_url=content.file_url,
        file_size=content.file_size,
        ai_summary=content.ai_summary,
        ai_keywords=content.ai_keywords or [],
        ai_status=AiStatus(content.ai_status),
        ai_error=content.ai_error,
        ai_processed_at=(
            str(content.ai_processed_at) if content.ai_processed_at else None
        ),
        uploaded_by=content.uploaded_by,
        uploaded_by_name=content.uploader.name if content.uploader else "未知",
        category_id=content.category_id,
        category_name=category.name if category else None,
        primary_category_name=(
            category.parent.name if category and category.parent else None
        ),
        created_at=str(content.created_at),
        updated_at=str(content.updated_at),
    )


async def semantic_search(
    db: AsyncSession,
    *,
    query_embedding: list[float],
    command: SearchContentCommand,
) -> list[SearchResultOutput]:
    """
    Search contents by cosine similarity against query_embedding.
    Returns list of SearchResultOutput sorted by relevance.
    Only searches approved content.
    """
    distance = Content.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Content.id, (1 - distance).label("score"))
        .where(Content.status == ContentStatus.approved)
        .where(Content.embedding.isnot(None))
        .order_by(distance)
        .limit(command.limit)
    )

    if command.content_type:
        stmt = stmt.where(Content.content_type == command.content_type)

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return []

    ids = [row.id for row in rows]
    scores = {row.id: row.score for row in rows}

    contents_result = await db.execute(
        select(Content)
        .where(Content.id.in_(ids))
        .options(
            selectinload(Content.tag_objects),
            selectinload(Content.category).selectinload(Category.parent),
            joinedload(Content.uploader),
        )
    )
    contents = {c.id: c for c in contents_result.scalars().all()}

    return [
        SearchResultOutput(
            content=_content_to_output(contents[row_id]), score=scores[row_id]
        )
        for row_id in ids
        if row_id in contents
    ]
