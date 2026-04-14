"""Multi-path retrieval: vector, FTS, and tag exact match."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.content import ContentStatus, ParsedQuery
from app.models.content import Content


@dataclass(slots=True)
class RecallItem:
    """A single item from a recall path."""

    content_id: int
    score: float = 0.0


@dataclass(slots=True)
class RecallResult:
    """Aggregated results from all recall paths."""

    vector_items: list[RecallItem] = field(default_factory=list)
    fts_items: list[RecallItem] = field(default_factory=list)
    tag_items: list[RecallItem] = field(default_factory=list)


async def recall_vector(
    db: AsyncSession,
    *,
    query_embedding: list[float],
    parsed: ParsedQuery,
) -> list[RecallItem]:
    """Recall by pgvector cosine similarity."""
    distance = Content.embedding.cosine_distance(query_embedding)

    stmt = (
        select(Content.id, (1 - distance).label("score"))
        .where(Content.status == ContentStatus.approved)
        .where(Content.embedding.isnot(None))
    )

    if parsed.parsed_content_type:
        stmt = stmt.where(Content.content_type == parsed.parsed_content_type)

    stmt = stmt.order_by(distance).limit(settings.SEARCH_VECTOR_RECALL_LIMIT)
    result = await db.execute(stmt)

    return [
        RecallItem(content_id=row.id, score=float(row.score)) for row in result.all()
    ]


async def recall_fts(
    db: AsyncSession,
    *,
    query_text: str,
    parsed: ParsedQuery,
) -> list[RecallItem]:
    """Recall by full-text search (zhparser or ILIKE fallback)."""
    if not query_text.strip():
        return []

    if settings.SEARCH_FTS_BACKEND == "zhparser":
        return await _recall_fts_zhparser(db, query_text=query_text, parsed=parsed)
    return await _recall_fts_ilike(db, query_text=query_text, parsed=parsed)


async def _recall_fts_zhparser(
    db: AsyncSession,
    *,
    query_text: str,
    parsed: ParsedQuery,
) -> list[RecallItem]:
    """FTS recall using PostgreSQL zhparser."""
    type_clause = ""
    params: dict[str, object] = {
        "query": query_text,
        "limit": settings.SEARCH_FTS_RECALL_LIMIT,
    }

    if parsed.parsed_content_type:
        type_clause = "AND content_type = :content_type"
        params["content_type"] = parsed.parsed_content_type

    sql = text(
        f"""
        SELECT id,
               ts_rank_cd(
                   to_tsvector('zhparser', search_document),
                   plainto_tsquery('zhparser', :query)
               ) AS fts_rank
        FROM contents
        WHERE status = 'approved'
          AND search_document IS NOT NULL
          AND to_tsvector('zhparser', search_document)
              @@ plainto_tsquery('zhparser', :query)
          {type_clause}
        ORDER BY fts_rank DESC
        LIMIT :limit
    """
    )

    result = await db.execute(sql, params)
    return [
        RecallItem(content_id=row.id, score=float(row.fts_rank)) for row in result.all()
    ]


async def _recall_fts_ilike(
    db: AsyncSession,
    *,
    query_text: str,
    parsed: ParsedQuery,
) -> list[RecallItem]:
    """Fallback FTS using ILIKE on search_document."""
    # Combine must_terms and should_terms for broader matching
    terms = parsed.must_terms + parsed.should_terms
    if not terms:
        terms = [query_text]

    # Build OR conditions for ILIKE matching
    conditions: list[str] = []
    params: dict[str, object] = {"limit": settings.SEARCH_FTS_RECALL_LIMIT}
    for i, term in enumerate(terms):
        param_key = f"term_{i}"
        conditions.append(f"search_document ILIKE :{param_key}")
        params[param_key] = f"%{term}%"

    if not conditions:
        return []

    where_terms = " OR ".join(conditions)
    type_clause = ""
    if parsed.parsed_content_type:
        type_clause = "AND content_type = :content_type"
        params["content_type"] = parsed.parsed_content_type

    sql = text(
        f"""
        SELECT id, 1.0 AS fts_rank
        FROM contents
        WHERE status = 'approved'
          AND search_document IS NOT NULL
          AND ({where_terms})
          {type_clause}
        LIMIT :limit
    """
    )

    result = await db.execute(sql, params)
    return [
        RecallItem(content_id=row.id, score=float(row.fts_rank)) for row in result.all()
    ]


async def recall_tags(
    db: AsyncSession,
    *,
    parsed: ParsedQuery,
) -> list[RecallItem]:
    """Recall by exact/phrase tag and AI keyword matching."""
    all_terms = parsed.must_terms + parsed.should_terms
    if not all_terms:
        return []

    matched_ids: dict[int, float] = {}

    # 1. Tag exact and phrase match
    for term in all_terms:
        # Exact match on tags
        tag_exact_sql = text(
            """
            SELECT ct.content_id
            FROM content_tags ct
            JOIN tags t ON t.id = ct.tag_id
            JOIN contents c ON c.id = ct.content_id
            WHERE LOWER(t.name) = LOWER(:term)
              AND c.status = 'approved'
        """
        )
        result = await db.execute(tag_exact_sql, {"term": term})
        for row in result.all():
            matched_ids[row.content_id] = matched_ids.get(row.content_id, 0) + 2.0

        # Phrase match on tags
        tag_phrase_sql = text(
            """
            SELECT ct.content_id
            FROM content_tags ct
            JOIN tags t ON t.id = ct.tag_id
            JOIN contents c ON c.id = ct.content_id
            WHERE LOWER(t.name) LIKE LOWER(:pattern)
              AND LOWER(t.name) != LOWER(:term)
              AND c.status = 'approved'
        """
        )
        result = await db.execute(
            tag_phrase_sql, {"pattern": f"%{term}%", "term": term}
        )
        for row in result.all():
            matched_ids[row.content_id] = matched_ids.get(row.content_id, 0) + 1.5

    # 2. AI keyword exact and phrase match
    for term in all_terms:
        kw_exact_sql = text(
            """
            SELECT id AS content_id
            FROM contents
            WHERE status = 'approved'
              AND ai_keywords IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(ai_keywords) kw
                  WHERE LOWER(kw) = LOWER(:term)
              )
        """
        )
        result = await db.execute(kw_exact_sql, {"term": term})
        for row in result.all():
            matched_ids[row.content_id] = matched_ids.get(row.content_id, 0) + 1.8

        kw_phrase_sql = text(
            """
            SELECT id AS content_id
            FROM contents
            WHERE status = 'approved'
              AND ai_keywords IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements_text(ai_keywords) kw
                  WHERE LOWER(kw) LIKE LOWER(:pattern)
                    AND LOWER(kw) != LOWER(:term)
              )
        """
        )
        result = await db.execute(kw_phrase_sql, {"pattern": f"%{term}%", "term": term})
        for row in result.all():
            matched_ids[row.content_id] = matched_ids.get(row.content_id, 0) + 1.0

    # Sort by match score descending, limit
    items = sorted(
        (RecallItem(content_id=cid, score=score) for cid, score in matched_ids.items()),
        key=lambda x: x.score,
        reverse=True,
    )
    return items[: settings.SEARCH_TAG_RECALL_LIMIT]
