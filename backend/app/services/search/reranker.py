"""Top-K LLM reranking for search results."""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings
from app.core.logging import fingerprint_text
from app.domains.content import ContentOutput, ParsedQuery

logger = logging.getLogger(__name__)


def _build_candidate_text(
    content: ContentOutput,
    *,
    initial_score: float,
    lexical_score: float,
    semantic_score: float,
    matched_signals: list[str],
) -> dict:
    """Build a compact representation of content for LLM reranking."""
    return {
        "id": content.id,
        "title": content.title or "",
        "content_type": content.content_type.value,
        "tags": content.tags[:12],
        "ai_keywords": content.ai_keywords[:15],
        "category": content.category_name or "",
        "primary_category": content.primary_category_name or "",
        "description": (content.description or "")[:180],
        "ai_summary": (content.ai_summary or "")[:180],
        "created_at": content.created_at,
        "updated_at": content.updated_at,
        "view_count": content.view_count,
        "download_count": content.download_count,
        "matched_signals": matched_signals[:12],
        "lexical_score": round(lexical_score, 2),
        "semantic_score": round(semantic_score, 2),
        "initial_score": round(initial_score, 1),
    }


async def rerank_with_llm(
    candidates: list[tuple[ContentOutput, float, float, float, list[str]]],
    parsed: ParsedQuery,
) -> list[int] | None:
    """Rerank top-K candidates using LLM.

    Args:
        candidates: List of (ContentOutput, initial_score, lexical_score,
            semantic_score, matched_signals) tuples.
        parsed: Parsed query for context.

    Returns:
        Reordered list of content IDs, or None if reranking failed/skipped.
    """
    if not settings.SEARCH_ENABLE_LLM_RERANK:
        return None
    if not parsed.need_llm_rerank:
        return None

    candidate_limit = settings.SEARCH_LLM_RERANK_CANDIDATE_LIMIT
    top_k = candidates[:candidate_limit]
    if len(top_k) <= 1:
        return None

    candidate_data = []
    for content, score, lexical_score, semantic_score, matched_signals in top_k:
        candidate_data.append(
            _build_candidate_text(
                content,
                initial_score=score,
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                matched_signals=matched_signals,
            )
        )

    sort_intent = parsed.sort_intent or "relevance"
    time_intent = json.dumps(parsed.time_intent, ensure_ascii=False)
    exclude_terms = "、".join(parsed.exclude_terms) if parsed.exclude_terms else "无"
    requested_count = parsed.limit_intent or "未指定"

    prompt = (
        "你是一个营销素材搜索结果重排模块。\n"
        f"用户查询：{parsed.raw_query}\n\n"
        "请基于用户意图，对候选素材进行综合重排，并只保留真正相关的素材。\n"
        f"显式排序意图：{sort_intent}\n"
        f"显式时间意图：{time_intent}\n"
        f"排除条件：{exclude_terms}\n"
        f"用户期望返回数量：{requested_count}\n\n"
        "重排原则：\n"
        "1. 优先满足用户明确提出的硬约束"
        "（例如最新、只要视频、不要图片、近一个月）。\n"
        "2. 在硬约束满足的前提下，再综合相关性、热度、下载量、匹配信号与已有分数。\n"
        "3. 如果候选素材不满足显式约束，"
        "或与用户核心主题明显不符，可以直接剔除，不要为了凑数量保留。\n"
        "4. 如果相关素材不足，可以少返回，绝不要用弱相关结果凑数。\n"
        "输出格式为 JSON 数组，只包含需要保留的素材 id，"
        "并按最终顺序排列，例如：[3, 1, 5]\n"
        "不要输出其他内容。\n\n"
        f"候选素材：\n{json.dumps(candidate_data, ensure_ascii=False)}"
    )

    from app.services.infrastructure.ai import _dashscope_compat

    try:
        response = await asyncio.wait_for(
            _dashscope_compat.chat.completions.create(
                model=settings.SEARCH_LLM_RERANK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                extra_body={"enable_thinking": False},
            ),
            timeout=settings.SEARCH_LLM_RERANK_TIMEOUT_S,
        )
        text = response.choices[0].message.content or ""
        reranked_ids = json.loads(text)
        if isinstance(reranked_ids, list) and all(
            isinstance(x, int) for x in reranked_ids
        ):
            return reranked_ids
        logger.warning("LLM rerank returned invalid format: %s", text)
        return None
    except TimeoutError:
        logger.warning(
            "LLM rerank timed out query_fp=%s query_len=%d",
            fingerprint_text(parsed.raw_query),
            len(parsed.raw_query),
        )
        return None
    except Exception:
        logger.warning(
            "LLM rerank failed query_fp=%s query_len=%d",
            fingerprint_text(parsed.raw_query),
            len(parsed.raw_query),
            exc_info=True,
        )
        return None
