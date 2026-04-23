"""Unified search orchestration for Web and Bot callers.

This module is the single entry point for query parsing, hybrid recall,
business scoring, and optional LLM reranking.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import settings
from app.core.logging import fingerprint_text
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
    """Convert an ORM content row into the public domain output."""
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


async def _run_recall_path(coro) -> tuple[list, float]:
    """Run one recall coroutine and return its items with elapsed ms."""
    started_at = time.monotonic()
    items = await coro
    return items, _ms_since(started_at)


async def _run_recall_with_session(
    session_factory: async_sessionmaker[AsyncSession],
    callback,
) -> tuple[list, float]:
    """Run a recall path with its own isolated AsyncSession."""
    async with session_factory() as recall_db:
        return await _run_recall_path(callback(recall_db))


async def search_contents(
    db: AsyncSession,
    *,
    command: SearchContentCommand,
) -> SearchOutput:
    """Execute the current unified search pipeline.

    Flow:
      1. Parse query intent and normalize terms
      2. Generate a single query embedding
      3. Run vector / FTS / tag recall concurrently with isolated sessions
      4. Fuse candidate IDs with RRF
      5. Apply business scoring on hydrated content rows
      6. Optionally let the reranker reorder or trim the candidate window
    """
    total_start = time.monotonic()

    parse_started_at = time.monotonic()
    parsed = await parse_query(command.query)

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
            sort_intent=parsed.sort_intent,
            time_intent=parsed.time_intent,
            exclude_terms=parsed.exclude_terms,
            limit_intent=parsed.limit_intent,
        )
    query_parse_ms = _ms_since(parse_started_at)

    final_limit = command.limit
    if command.allow_query_limit_override and parsed.limit_intent is not None:
        final_limit = max(parsed.limit_intent, 1)

    embedding_started_at = time.monotonic()
    query_embedding = await generate_embedding(parsed.query_embedding_text)
    embedding_ms = _ms_since(embedding_started_at)

    recall_bind = db.bind
    if recall_bind is None:
        raise RuntimeError("Search recall requires an active database bind")

    recall_engine: AsyncEngine
    if isinstance(recall_bind, AsyncConnection):
        recall_engine = recall_bind.engine
    else:
        recall_engine = recall_bind

    recall_session_factory = async_sessionmaker(recall_engine, expire_on_commit=False)

    (
        (vector_items, vector_recall_ms),
        (fts_items, fts_recall_ms),
        (tag_items, tag_recall_ms),
    ) = await asyncio.gather(
        _run_recall_with_session(
            recall_session_factory,
            lambda recall_db: recall_vector(
                recall_db,
                query_embedding=query_embedding,
                parsed=parsed,
            ),
        ),
        _run_recall_with_session(
            recall_session_factory,
            lambda recall_db: recall_fts(
                recall_db,
                query_text=parsed.normalized_query,
                parsed=parsed,
            ),
        ),
        _run_recall_with_session(
            recall_session_factory,
            lambda recall_db: recall_tags(recall_db, parsed=parsed),
        ),
    )

    merge_started_at = time.monotonic()
    rrf_scores = rrf_merge(vector_items, fts_items, tag_items)
    rrf_merge_ms = _ms_since(merge_started_at)

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
        _log_timing(
            timing,
            embedding_ms=embedding_ms,
            parsed=parsed,
            vector_hits=len(vector_items),
            fts_hits=len(fts_items),
            tag_hits=len(tag_items),
            candidate_count=0,
            result_count=0,
            reranked=False,
        )
        return SearchOutput(
            results=[],
            timing=timing if settings.SEARCH_DEBUG_TIMING else None,
            query_info=parsed,
        )

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
    contents_map = {
        content.id: content for content in contents_result.unique().scalars().all()
    }

    vector_scores = {item.content_id: item.score for item in vector_items}
    fts_scores = {item.content_id: item.score for item in fts_items}
    max_fts_rank = max((item.score for item in fts_items), default=0.0)

    scoring_started_at = time.monotonic()
    scored: list[tuple[ContentOutput, float, float, float, list[str]]] = []

    for content_id in candidate_ids:
        orm_content = contents_map.get(content_id)
        if orm_content is None:
            continue

        content_output = _content_to_output(orm_content)
        fts_rank = fts_scores.get(content_id, 0.0)
        vector_similarity = vector_scores.get(content_id, 0.0)

        final_score, signals = compute_business_score(
            content_output,
            parsed,
            fts_rank=fts_rank,
            max_fts_rank=max_fts_rank,
            vector_similarity=vector_similarity,
            hot_score=orm_content.hot_score,
        )
        final_score += rrf_scores.get(content_id, 0.0) * 100

        lexical_score = 0.0
        if max_fts_rank > 0 and fts_rank > 0:
            lexical_score = round(
                (fts_rank / max_fts_rank) * settings.SEARCH_SCORE_FTS_MAX,
                2,
            )
        semantic_score = round(
            vector_similarity * settings.SEARCH_SCORE_VECTOR_MAX,
            2,
        )

        scored.append(
            (content_output, final_score, lexical_score, semantic_score, signals)
        )

    scored.sort(key=lambda item: item[1], reverse=True)
    scoring_ms = _ms_since(scoring_started_at)

    rerank_started_at = time.monotonic()
    llm_rerank_ms: float | None = None
    reranked = False

    reranked_ids = await rerank_with_llm(list(scored), parsed)
    if reranked_ids is not None:
        reranked = True
        llm_rerank_ms = _ms_since(rerank_started_at)

        id_to_scored = {item[0].id: item for item in scored}
        reordered: list[tuple[ContentOutput, float, float, float, list[str]]] = []
        seen: set[int] = set()

        # The reranker may intentionally drop weak matches. In that case we keep
        # its filtered subset instead of re-attaching the original tail.
        for content_id in reranked_ids:
            if content_id in id_to_scored and content_id not in seen:
                reordered.append(id_to_scored[content_id])
                seen.add(content_id)

        scored = reordered
    else:
        llm_rerank_ms = (
            _ms_since(rerank_started_at) if settings.SEARCH_ENABLE_LLM_RERANK else None
        )

    results: list[SearchResultOutput] = []
    for content_output, final_score, lexical_score, semantic_score, signals in scored[
        :final_limit
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
    _log_timing(
        timing,
        embedding_ms=embedding_ms,
        parsed=parsed,
        vector_hits=len(vector_items),
        fts_hits=len(fts_items),
        tag_hits=len(tag_items),
        candidate_count=len(candidate_ids),
        result_count=len(results),
        reranked=reranked,
    )

    return SearchOutput(
        results=results,
        timing=timing if settings.SEARCH_DEBUG_TIMING else None,
        query_info=parsed,
    )


def _log_timing(
    timing: SearchTimingOutput,
    *,
    embedding_ms: float | None = None,
    parsed: ParsedQuery | None = None,
    vector_hits: int | None = None,
    fts_hits: int | None = None,
    tag_hits: int | None = None,
    candidate_count: int | None = None,
    result_count: int | None = None,
    reranked: bool | None = None,
) -> None:
    """Emit structured timing logs for each search request."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": "INFO",
        "logger": logger.name,
        "message": "search_timing",
        "query_fp": fingerprint_text(parsed.raw_query) if parsed else None,
        "query_len": len(parsed.raw_query) if parsed else None,
        "llm_used": parsed.llm_used if parsed else None,
        "parsed_content_type": parsed.parsed_content_type if parsed else None,
        "sort_intent": parsed.sort_intent if parsed else None,
        "limit_intent": parsed.limit_intent if parsed else None,
        "exclude_term_count": len(parsed.exclude_terms) if parsed else None,
        "must_term_count": len(parsed.must_terms) if parsed else None,
        "should_term_count": len(parsed.should_terms) if parsed else None,
        "must_term_fps": (
            [fingerprint_text(term) for term in parsed.must_terms] if parsed else None
        ),
        "should_term_fps": (
            [fingerprint_text(term) for term in parsed.should_terms] if parsed else None
        ),
        "embedding_ms": embedding_ms,
        "query_parse_ms": timing.query_parse_ms,
        "vector_recall_ms": timing.vector_recall_ms,
        "fts_recall_ms": timing.fts_recall_ms,
        "tag_recall_ms": timing.tag_recall_ms,
        "rrf_merge_ms": timing.rrf_merge_ms,
        "scoring_ms": timing.scoring_ms,
        "llm_rerank_ms": timing.llm_rerank_ms,
        "vector_hits": vector_hits,
        "fts_hits": fts_hits,
        "tag_hits": tag_hits,
        "candidate_count": candidate_count,
        "result_count": result_count,
        "reranked": reranked,
        "total_ms": timing.total_ms,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
