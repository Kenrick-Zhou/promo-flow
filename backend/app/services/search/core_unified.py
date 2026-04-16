"""Unified search service.

Orchestrates query understanding, multi-path recall, scoring, and reranking.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import settings
from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    ParsedQuery,
    SearchContentCommand,
    SearchOutput,
    SearchResultOutput,
    SearchTimingOutput,
)
from app.models.category import Category
from app.models.content import Content
from app.services.infrastructure.ai import generate_embedding
from app.services.infrastructure.storage import get_public_url
from app.services.search.query_parser import parse_query
from app.services.search.ranker import compute_business_score, rrf_merge
from app.services.search.reranker import rerank_with_llm
from app.services.search.retriever import recall_fts, recall_tags, recall_vector

logger = logging.getLogger(__name__)


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
        file_url=content.file_url or get_public_url(content.file_key),
        file_size=content.file_size,
        media_width=content.media_width,
        media_height=content.media_height,
        view_count=content.view_count,
        download_count=content.download_count,
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


def _ms_since(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)


async def search_contents(
    db: AsyncSession,
    *,
    command: SearchContentCommand,
) -> SearchOutput:
    """Unified search entry point for both Web and Bot.

    Pipeline:
      1. Query understanding (rules + optional LLM)
      2. Multi-path recall (vector + FTS + tag)
      3. RRF fusion
      4. Business scoring
      5. Optional LLM reranking
    """
    total_start = time.monotonic()

    # ── 1. Query understanding ───────────────────────────────
    t0 = time.monotonic()
    parsed = await parse_query(command.query)

    # Override content_type if explicitly provided by client
    if command.content_type:
        parsed = ParsedQuery(
            raw_query=parsed.raw_query,
            normalized_query=parsed.normalized_query,
            parsed_content_type=command.content_type,
            must_terms=parsed.must_terms,
            should_terms=parsed.should_terms,
            query_embedding_text=parsed.query_embedding_text,
            need_llm_rerank=parsed.need_llm_rerank,
            llm_used=parsed.llm_used,
        )
    query_parse_ms = _ms_since(t0)

    # ── 2. Generate embedding ────────────────────────────────
    t0 = time.monotonic()
    query_embedding = await generate_embedding(parsed.query_embedding_text)
    embedding_ms = _ms_since(t0)

    # ── 3. Multi-path recall ─────────────────────────────────
    t0 = time.monotonic()
    vector_items = await recall_vector(
        db, query_embedding=query_embedding, parsed=parsed
    )
    vector_recall_ms = _ms_since(t0)

    t0 = time.monotonic()
    fts_items = await recall_fts(db, query_text=parsed.normalized_query, parsed=parsed)
    fts_recall_ms = _ms_since(t0)

    t0 = time.monotonic()
    tag_items = await recall_tags(db, parsed=parsed)
    tag_recall_ms = _ms_since(t0)

    # ── 4. RRF fusion ────────────────────────────────────────
    t0 = time.monotonic()
    rrf_scores = rrf_merge(vector_items, fts_items, tag_items)
    rrf_merge_ms = _ms_since(t0)

    if not rrf_scores:
        timing = SearchTimingOutput(
            query_parse_ms=query_parse_ms,
            vector_recall_ms=vector_recall_ms + embedding_ms,
            fts_recall_ms=fts_recall_ms,
            tag_recall_ms=tag_recall_ms,
            rrf_merge_ms=rrf_merge_ms,
            scoring_ms=0,
            llm_rerank_ms=None,
            total_ms=_ms_since(total_start),
        )
        _log_timing(timing)
        return SearchOutput(
            results=[],
            timing=timing if settings.SEARCH_DEBUG_TIMING else None,
            query_info=parsed,
        )

    # ── 5. Load content objects ──────────────────────────────
    candidate_ids = list(rrf_scores.keys())
    contents_result = await db.execute(
        select(Content)
        .where(Content.id.in_(candidate_ids))
        .options(
            selectinload(Content.tag_objects),
            selectinload(Content.category).selectinload(Category.parent),
            joinedload(Content.uploader),
        )
    )
    contents_map = {c.id: c for c in contents_result.unique().scalars().all()}

    # Build lookup maps for scores
    vector_scores: dict[int, float] = {
        item.content_id: item.score for item in vector_items
    }
    fts_scores: dict[int, float] = {item.content_id: item.score for item in fts_items}
    max_fts_rank = max((item.score for item in fts_items), default=0.0)

    # ── 6. Business scoring ──────────────────────────────────
    t0 = time.monotonic()
    scored: list[tuple[ContentOutput, float, float, float, list[str]]] = []

    for content_id in candidate_ids:
        orm_content = contents_map.get(content_id)
        if not orm_content:
            continue

        content_output = _content_to_output(orm_content)
        fts_rank = fts_scores.get(content_id, 0.0)
        vector_sim = vector_scores.get(content_id, 0.0)

        final_score, signals = compute_business_score(
            content_output,
            parsed,
            fts_rank=fts_rank,
            max_fts_rank=max_fts_rank,
            vector_similarity=vector_sim,
        )

        # Add RRF base score
        final_score += rrf_scores.get(content_id, 0) * 100

        lexical_score = 0.0
        if max_fts_rank > 0 and fts_rank > 0:
            lexical_score = round(
                (fts_rank / max_fts_rank) * settings.SEARCH_SCORE_FTS_MAX, 2
            )
        semantic_score = round(vector_sim * settings.SEARCH_SCORE_VECTOR_MAX, 2)

        scored.append(
            (content_output, final_score, lexical_score, semantic_score, signals)
        )

    # Sort by final_score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    scoring_ms = _ms_since(t0)

    # ── 7. Optional LLM reranking ────────────────────────────
    t0 = time.monotonic()
    llm_rerank_ms: float | None = None
    reranked = False

    top_for_rerank = [(c, s) for c, s, _, _, _ in scored]
    reranked_ids = await rerank_with_llm(top_for_rerank, parsed)

    if reranked_ids is not None:
        reranked = True
        llm_rerank_ms = _ms_since(t0)

        # Build reordered results using LLM ranking for top-K
        id_to_scored = {item[0].id: item for item in scored}
        reordered: list[tuple[ContentOutput, float, float, float, list[str]]] = []
        seen: set[int] = set()

        for cid in reranked_ids:
            if cid in id_to_scored and cid not in seen:
                reordered.append(id_to_scored[cid])
                seen.add(cid)

        # Append remaining items not in reranked list
        for item in scored:
            if item[0].id not in seen:
                reordered.append(item)

        scored = reordered
    else:
        llm_rerank_ms = _ms_since(t0) if settings.SEARCH_ENABLE_LLM_RERANK else None

    # ── 8. Build results ─────────────────────────────────────
    results: list[SearchResultOutput] = []
    for content_output, final_score, lexical_score, semantic_score, signals in scored[
        : command.limit
    ]:
        results.append(
            SearchResultOutput(
                content=content_output,
                final_score=round(final_score, 2),
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                matched_signals=signals,
                reranked=reranked,
            )
        )

    timing = SearchTimingOutput(
        query_parse_ms=query_parse_ms,
        vector_recall_ms=vector_recall_ms + embedding_ms,
        fts_recall_ms=fts_recall_ms,
        tag_recall_ms=tag_recall_ms,
        rrf_merge_ms=rrf_merge_ms,
        scoring_ms=scoring_ms,
        llm_rerank_ms=llm_rerank_ms,
        total_ms=_ms_since(total_start),
    )
    _log_timing(timing)

    return SearchOutput(
        results=results,
        timing=timing if settings.SEARCH_DEBUG_TIMING else None,
        query_info=parsed,
    )


def _log_timing(timing: SearchTimingOutput) -> None:
    """Log structured timing data."""
    logger.info(
        "search_timing query_parse=%.1fms vector=%.1fms fts=%.1fms "
        "tag=%.1fms rrf=%.1fms scoring=%.1fms rerank=%s total=%.1fms",
        timing.query_parse_ms,
        timing.vector_recall_ms,
        timing.fts_recall_ms,
        timing.tag_recall_ms,
        timing.rrf_merge_ms,
        timing.scoring_ms,
        f"{timing.llm_rerank_ms:.1f}ms" if timing.llm_rerank_ms is not None else "N/A",
        timing.total_ms,
    )
