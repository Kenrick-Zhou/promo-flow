"""Top-K LLM reranking for search results."""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings
from app.domains.content import ContentOutput, ParsedQuery

logger = logging.getLogger(__name__)


def _build_candidate_text(content: ContentOutput) -> dict:
    """Build a compact representation of content for LLM reranking."""
    return {
        "id": content.id,
        "title": content.title or "",
        "content_type": content.content_type.value,
        "tags": content.tags[:10],
        "ai_keywords": content.ai_keywords[:10],
        "category": content.category_name or "",
        "description": (content.description or "")[:100],
        "ai_summary": (content.ai_summary or "")[:100],
    }


async def rerank_with_llm(
    candidates: list[tuple[ContentOutput, float]],
    parsed: ParsedQuery,
) -> list[int] | None:
    """Rerank top-K candidates using LLM.

    Args:
        candidates: List of (ContentOutput, initial_score) tuples.
        parsed: Parsed query for context.

    Returns:
        Reordered list of content IDs, or None if reranking failed/skipped.
    """
    if not settings.SEARCH_ENABLE_LLM_RERANK:
        return None
    if not parsed.need_llm_rerank:
        return None

    top_k = candidates[: settings.SEARCH_LLM_RERANK_TOP_K]
    if len(top_k) <= 1:
        return None

    candidate_data = []
    for content, score in top_k:
        entry = _build_candidate_text(content)
        entry["initial_score"] = round(score, 1)
        candidate_data.append(entry)

    prompt = (
        "你是一个营销素材搜索结果重排模块。\n"
        f"用户查询：{parsed.raw_query}\n\n"
        "请从以下候选素材中，按照与用户查询的相关性从高到低重新排序。\n"
        "输出格式为 JSON 数组，只包含素材 id，例如：[3, 1, 5, 2, 4]\n"
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
        logger.warning("LLM rerank timed out for query: %s", parsed.raw_query)
        return None
    except Exception:
        logger.warning(
            "LLM rerank failed for query: %s", parsed.raw_query, exc_info=True
        )
        return None
