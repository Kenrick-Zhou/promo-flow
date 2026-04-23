"""Multi-path retrieval helpers for vector, FTS, and tag/keyword matching."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domains.content import ContentStatus, ParsedQuery
from app.models.content import Content

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RecallItem:
    """A single item from a recall path."""

    content_id: int
    score: float = 0.0


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
    """Recall by PostgreSQL FTS or ILIKE fallback."""
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
    """FTS recall using a configured PostgreSQL text search config."""
    ts_config = settings.SEARCH_FTS_ZH_TSCONFIG
    type_clause = ""
    params: dict[str, object] = {
        "query": query_text,
        "limit": settings.SEARCH_FTS_RECALL_LIMIT,
        "ts_config": ts_config,
    }

    if parsed.parsed_content_type:
        type_clause = "AND content_type = :content_type"
        params["content_type"] = parsed.parsed_content_type

    sql = text(
        f"""
        SELECT id,
               ts_rank_cd(
                   to_tsvector(CAST(:ts_config AS regconfig), search_document),
                   plainto_tsquery(CAST(:ts_config AS regconfig), :query)
               ) AS fts_rank
        FROM contents
        WHERE status = 'approved'
          AND search_document IS NOT NULL
          AND to_tsvector(CAST(:ts_config AS regconfig), search_document)
              @@ plainto_tsquery(CAST(:ts_config AS regconfig), :query)
          {type_clause}
        ORDER BY fts_rank DESC
        LIMIT :limit
    """
    )

    try:
        result = await db.execute(sql, params)
    except DBAPIError as exc:
        if _is_missing_text_search_config_error(exc):
            await db.rollback()
            logger.warning(
                "PostgreSQL FTS config '%s' unavailable; falling back to ILIKE",
                ts_config,
            )
            return await _recall_fts_ilike(db, query_text=query_text, parsed=parsed)
        raise

    return [
        RecallItem(content_id=row.id, score=float(row.fts_rank)) for row in result.all()
    ]


def _is_missing_text_search_config_error(exc: DBAPIError) -> bool:
    """Return True when the configured PostgreSQL text search config is unavailable."""
    message_parts = [str(exc)]
    if getattr(exc, "orig", None) is not None:
        message_parts.append(str(exc.orig))

    message = "\n".join(message_parts).lower()
    return "text search configuration" in message and "does not exist" in message


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
    """Recall by exact/phrase tag names plus AI keyword matches."""
    all_terms = list(dict.fromkeys(parsed.must_terms + parsed.should_terms))
    if not all_terms:
        return []

    term_cte_parts: list[str] = []
    params: dict[str, object] = {"limit": settings.SEARCH_TAG_RECALL_LIMIT}
    for idx, term in enumerate(all_terms):
        param_name = f"term_{idx}"
        term_cte_parts.append(f"SELECT LOWER(:{param_name}) AS term")
        params[param_name] = term

    term_cte_sql = "\n            UNION ALL\n            ".join(term_cte_parts)
    type_clause = ""
    if parsed.parsed_content_type:
        type_clause = "AND c.content_type = :content_type"
        params["content_type"] = parsed.parsed_content_type

    sql = text(
        f"""
        WITH term_inputs AS (
            SELECT DISTINCT term
            FROM (
                {term_cte_sql}
            ) AS input_terms
            WHERE term <> ''
        ),
        matches AS (
            SELECT ct.content_id,
                   CASE
                       WHEN LOWER(t.name) = ti.term THEN 2.0
                       ELSE 1.5
                   END AS score
            FROM term_inputs ti
            JOIN tags t
              ON LOWER(t.name) = ti.term
              OR (
                  LOWER(t.name) LIKE ('%' || ti.term || '%')
                  AND LOWER(t.name) != ti.term
              )
            JOIN content_tags ct ON ct.tag_id = t.id
            JOIN contents c ON c.id = ct.content_id
            WHERE c.status = 'approved'
                            {type_clause}

            UNION ALL

            SELECT c.id AS content_id,
                   CASE
                       WHEN LOWER(kw.keyword) = ti.term THEN 1.8
                       ELSE 1.0
                   END AS score
            FROM term_inputs ti
            JOIN contents c
              ON c.status = 'approved'
             AND c.ai_keywords IS NOT NULL
                         {type_clause}
            CROSS JOIN LATERAL jsonb_array_elements_text(c.ai_keywords) AS kw(keyword)
            WHERE LOWER(kw.keyword) = ti.term
               OR (
                   LOWER(kw.keyword) LIKE ('%' || ti.term || '%')
                   AND LOWER(kw.keyword) != ti.term
               )
        )
        SELECT content_id, SUM(score) AS score
        FROM matches
        GROUP BY content_id
        ORDER BY score DESC, content_id ASC
        LIMIT :limit
    """
    )

    result = await db.execute(sql, params)
    return [
        RecallItem(content_id=row.content_id, score=float(row.score))
        for row in result.all()
    ]
