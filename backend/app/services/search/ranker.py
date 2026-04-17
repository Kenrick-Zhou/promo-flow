"""RRF fusion and business scoring."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import settings
from app.domains.content import ContentOutput, ParsedQuery
from app.services.search.retriever import RecallItem


def rrf_merge(
    *recall_lists: list[RecallItem],
    k: int | None = None,
) -> dict[int, float]:
    """Reciprocal Rank Fusion across multiple recall lists.

    Returns dict of content_id → RRF score.
    """
    rrf_k = k if k is not None else settings.SEARCH_RRF_K
    scores: dict[int, float] = {}

    for recall_list in recall_lists:
        for rank, item in enumerate(recall_list, start=1):
            scores[item.content_id] = scores.get(item.content_id, 0) + 1.0 / (
                rrf_k + rank
            )

    return scores


def compute_business_score(
    content: ContentOutput,
    parsed: ParsedQuery,
    *,
    fts_rank: float,
    max_fts_rank: float,
    vector_similarity: float,
) -> tuple[float, list[str]]:
    """Compute business-weighted score for a single content.

    Returns (final_score, matched_signals).
    """
    s = settings
    score = 0.0
    signals: list[str] = []

    all_terms = parsed.must_terms + parsed.should_terms
    lower_terms = [t.lower() for t in all_terms]
    must_lower = [t.lower() for t in parsed.must_terms]

    # ── score_filter: content type match ─────────────────────
    if (
        parsed.parsed_content_type
        and content.content_type.value == parsed.parsed_content_type
    ):
        score += s.SEARCH_SCORE_CONTENT_TYPE_MATCH
        signals.append("content_type_filter")

    # ── score_exact: tags ────────────────────────────────────
    content_tags_lower = [t.lower() for t in content.tags]
    for term in lower_terms:
        for tag in content_tags_lower:
            if term == tag:
                score += s.SEARCH_SCORE_TAG_EXACT
                signals.append(f"tag_exact:{tag}")
            elif term in tag:
                score += s.SEARCH_SCORE_TAG_PHRASE
                signals.append(f"tag_phrase:{tag}")

    # ── score_exact: AI keywords ─────────────────────────────
    ai_kw_lower = [kw.lower() for kw in content.ai_keywords]
    for term in lower_terms:
        for kw in ai_kw_lower:
            if term == kw:
                score += s.SEARCH_SCORE_AI_KEYWORD_EXACT
                signals.append(f"ai_keyword_exact:{kw}")
            elif term in kw:
                score += s.SEARCH_SCORE_AI_KEYWORD_PHRASE
                signals.append(f"ai_keyword_phrase:{kw}")

    # ── score_exact: title ───────────────────────────────────
    title_lower = (content.title or "").lower()
    if title_lower:
        for term in lower_terms:
            if term == title_lower:
                score += s.SEARCH_SCORE_TITLE_EXACT
                signals.append("title_exact")
            elif term in title_lower:
                score += s.SEARCH_SCORE_TITLE_PHRASE
                signals.append("title_phrase")

    # ── score_exact: category ────────────────────────────────
    for cat_name in [content.category_name, content.primary_category_name]:
        if not cat_name:
            continue
        cat_lower = cat_name.lower()
        for term in lower_terms:
            if term == cat_lower:
                score += s.SEARCH_SCORE_CATEGORY_EXACT
                signals.append(f"category_match:{cat_name}")
            elif term in cat_lower:
                score += s.SEARCH_SCORE_CATEGORY_PHRASE
                signals.append(f"category_match:{cat_name}")

    # ── must_term matches in description and summary ─────────
    desc_lower = (content.description or "").lower()
    summary_lower = (content.ai_summary or "").lower()
    for term in must_lower:
        if term in desc_lower:
            score += s.SEARCH_SCORE_MUST_TERM_DESC
            signals.append(f"must_term:{term}")
        if term in summary_lower:
            score += s.SEARCH_SCORE_MUST_TERM_SUMMARY
            signals.append(f"must_term:{term}")

    # ── score_lexical: FTS normalized ────────────────────────
    lexical_score = 0.0
    if max_fts_rank > 0 and fts_rank > 0:
        lexical_score = (fts_rank / max_fts_rank) * s.SEARCH_SCORE_FTS_MAX
        score += lexical_score
        signals.append("fts_match")

    # ── score_semantic: vector normalized ────────────────────
    semantic_score = 0.0
    if vector_similarity > 0:
        semantic_score = vector_similarity * s.SEARCH_SCORE_VECTOR_MAX
        score += semantic_score
        signals.append("vector_match")

    # ── score_freshness ──────────────────────────────────────
    try:
        created = datetime.fromisoformat(content.created_at)
        age_days = (datetime.now(UTC) - created).days
        if age_days < 30:
            score += s.SEARCH_SCORE_FRESHNESS_MAX
        elif age_days < 90:
            score += s.SEARCH_SCORE_FRESHNESS_MAX * 0.5

        if parsed.sort_intent == "recent":
            if age_days <= 7:
                score += s.SEARCH_SCORE_FRESHNESS_MAX * 6
                signals.append("sort_recent:7d")
            elif age_days <= 30:
                score += s.SEARCH_SCORE_FRESHNESS_MAX * 4
                signals.append("sort_recent:30d")
            elif age_days <= 90:
                score += s.SEARCH_SCORE_FRESHNESS_MAX * 2
                signals.append("sort_recent:90d")

        if parsed.time_intent and parsed.time_intent.get("type") == "relative_days":
            limit_days = parsed.time_intent.get("days")
            if isinstance(limit_days, int):
                if age_days <= limit_days:
                    score += s.SEARCH_SCORE_FRESHNESS_MAX * 2
                    signals.append(f"time_window:{limit_days}d")
                else:
                    score *= 0.6
                    signals.append(f"time_window_miss:{limit_days}d")
    except (ValueError, TypeError):
        pass

    # ── must_terms penalty ───────────────────────────────────
    if must_lower:
        hit_any = False
        searchable = (
            f"{title_lower} {desc_lower} {summary_lower}"
            f" {' '.join(content_tags_lower)} {' '.join(ai_kw_lower)}"
        )
        for term in must_lower:
            if term in searchable:
                hit_any = True
                break
        if not hit_any:
            score *= 0.3

    return score, signals
