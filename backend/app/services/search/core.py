"""Semantic search service using pgvector cosine similarity."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content import (
    ContentOutput,
    ContentStatus,
    ContentType,
    SearchContentCommand,
    SearchResultOutput,
)
from app.models.content import Content


def _content_to_output(content: Content) -> ContentOutput:
    """Convert ORM Content to domain output."""
    return ContentOutput(
        id=content.id,
        title=content.title,
        description=content.description,
        tags=content.tags or [],
        content_type=ContentType(content.content_type),
        status=ContentStatus(content.status),
        file_key=content.file_key,
        file_url=content.file_url,
        file_size=content.file_size,
        ai_summary=content.ai_summary,
        ai_keywords=content.ai_keywords or [],
        uploaded_by=content.uploaded_by,
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
    vector_literal = f"[{','.join(str(v) for v in query_embedding)}]"

    # Use parameterized query for content_type filter
    base_filters = "status = 'approved' AND embedding IS NOT NULL"
    params: dict = {"embedding": vector_literal, "limit": command.limit}

    if command.content_type:
        base_filters += " AND content_type = :content_type"
        params["content_type"] = command.content_type

    stmt = text(
        f"""
        SELECT id, 1 - (embedding <=> :embedding::vector) AS score
        FROM contents
        WHERE {base_filters}
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
    """
    )

    result = await db.execute(stmt, params)
    rows = result.fetchall()

    if not rows:
        return []

    ids = [row.id for row in rows]
    scores = {row.id: row.score for row in rows}

    contents_result = await db.execute(select(Content).where(Content.id.in_(ids)))
    contents = {c.id: c for c in contents_result.scalars().all()}

    return [
        SearchResultOutput(
            content=_content_to_output(contents[row_id]), score=scores[row_id]
        )
        for row_id in ids
        if row_id in contents
    ]
