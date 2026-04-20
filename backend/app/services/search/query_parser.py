"""Query understanding: rule-based parsing + optional LLM enhancement."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.core.config import settings
from app.core.logging import fingerprint_text
from app.domains.content import ParsedQuery
from app.services.search.dictionaries.content_type import CONTENT_TYPE_KEYWORD_MAP
from app.services.search.dictionaries.stopwords import STOPWORDS
from app.services.search.dictionaries.synonyms import SYNONYM_DICT

logger = logging.getLogger(__name__)

# CJK Unicode ranges for segmentation
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")
_ALPHA_NUM_PATTERN = re.compile(r"[a-zA-Z0-9]+")
_COUNT_PATTERN = re.compile(
    r"(?:top\s*)?(\d{1,2})\s*(?:个|条|份|组|张|段|个视频|条视频)?",
    re.IGNORECASE,
)
_CHINESE_COUNT_PATTERN = re.compile(
    r"(?:top\s*)?(十|两|俩|[一二三四五六七八九])\s*(?:个|条|份|组|张|段|个视频|条视频)?"
)
_RECENT_DAYS_PATTERN = re.compile(r"(?:最近|近)(\d{1,3})\s*(天|周|个月|月)")
_EXCLUDE_PATTERNS = [
    re.compile(r"不要([^，。,；;？?]+)"),
    re.compile(r"除了([^，。,；;？?]+?)(?:以外|之外|外)"),
]
_SORT_RECENT_KEYWORDS = ("最新", "最近", "近期", "新一点", "新点")
_SORT_HOT_KEYWORDS = ("最热", "热门", "热度高", "高热度", "爆款")
_REQUEST_PREFIX_PATTERN = re.compile(
    r"^(给我|帮我|发我|推荐|列出|返回|找一下|找下|找找|找)\s*"
)
_LEADING_FILLER_PATTERN = re.compile(r"^(的|和|与|关于)\s*")
_CHINESE_COUNT_MAP = {
    "一": 1,
    "二": 2,
    "两": 2,
    "俩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _normalize_spacing(text: str) -> str:
    """Normalize spaces after stripping control phrases."""
    return re.sub(r"\s+", " ", text).strip(" ，,。；;!?！？")


def _strip_request_prefix(text: str) -> str:
    """Strip imperative request prefixes from the beginning of a query."""
    cleaned = _REQUEST_PREFIX_PATTERN.sub("", text, count=1)
    cleaned = _LEADING_FILLER_PATTERN.sub("", cleaned, count=1)
    return _normalize_spacing(cleaned)


def _simple_tokenize(text: str) -> list[str]:
    """Simple tokenizer: extract CJK character n-grams (bigrams) and ascii words."""
    tokens: list[str] = []

    # Extract ascii/number words
    for match in _ALPHA_NUM_PATTERN.finditer(text.lower()):
        word = match.group()
        if len(word) >= 2:
            tokens.append(word)

    # For CJK, use character bigrams as basic segmentation
    for match in _CJK_PATTERN.finditer(text):
        chars = match.group()
        if len(chars) >= 2:
            for i in range(len(chars) - 1):
                bigram = chars[i : i + 2]
                tokens.append(bigram)
            # Also keep the whole CJK span if short enough to be a word
            if 2 <= len(chars) <= 6:
                tokens.append(chars)
        elif len(chars) == 1:
            tokens.append(chars)

    return tokens


def _extract_content_type(query: str) -> tuple[str | None, str]:
    """Extract content type keyword from query, return (type, cleaned_query)."""
    # Sort by keyword length descending to match longest first
    sorted_keywords = sorted(CONTENT_TYPE_KEYWORD_MAP.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in query:
            content_type = CONTENT_TYPE_KEYWORD_MAP[keyword]
            cleaned = query.replace(keyword, "", 1).strip()
            return content_type, cleaned
    return None, query


def _extract_terms(query: str) -> list[str]:
    """Extract meaningful terms from query, filtering stopwords."""
    tokens = _simple_tokenize(query)
    # Deduplicate while preserving order
    seen: set[str] = set()
    terms: list[str] = []
    for token in tokens:
        if token not in STOPWORDS and token not in seen and len(token) >= 2:
            seen.add(token)
            terms.append(token)
    return terms


def _expand_synonyms(terms: list[str]) -> list[str]:
    """Expand terms using synonym dictionary."""
    expanded: list[str] = []
    seen: set[str] = set(terms)
    for term in terms:
        if term in SYNONYM_DICT:
            synonym = SYNONYM_DICT[term]
            if synonym not in seen:
                expanded.append(synonym)
                seen.add(synonym)
    return expanded


def _extract_time_intent(query: str) -> tuple[dict[str, str | int] | None, str]:
    """Extract explicit time window hints from query."""
    match = _RECENT_DAYS_PATTERN.search(query)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        days = amount
        if unit == "周":
            days = amount * 7
        elif unit in {"个月", "月"}:
            days = amount * 30
        cleaned = _normalize_spacing(query.replace(match.group(0), " ", 1))
        return {"type": "relative_days", "days": days, "label": match.group(0)}, cleaned

    shortcuts = [
        ("最近三个月", 90),
        ("近三个月", 90),
        ("最近一个月", 30),
        ("近一个月", 30),
        ("最近一周", 7),
        ("近一周", 7),
        ("这个月", 30),
        ("本月", 30),
        ("本周", 7),
        ("这周", 7),
    ]
    for phrase, days in shortcuts:
        if phrase in query:
            cleaned = _normalize_spacing(query.replace(phrase, " ", 1))
            return {"type": "relative_days", "days": days, "label": phrase}, cleaned

    return None, query


def _extract_exclude_terms(query: str) -> tuple[list[str], str]:
    """Extract excluded terms like '不要图片' from query."""
    exclude_terms: list[str] = []
    cleaned = query

    for pattern in _EXCLUDE_PATTERNS:
        for match in pattern.finditer(query):
            term = match.group(1).strip(" 的,，。；;!?！？")
            if term:
                exclude_terms.append(term)
                cleaned = cleaned.replace(match.group(0), " ", 1)

    deduped = list(dict.fromkeys(exclude_terms))
    return deduped, _normalize_spacing(cleaned)


def _extract_limit_intent(query: str) -> tuple[int | None, str]:
    """Extract requested result count without constraining rerank pool."""
    explicit = re.search(r"top\s*(\d{1,2})", query, re.IGNORECASE)
    if explicit:
        count = int(explicit.group(1))
        cleaned = _normalize_spacing(query.replace(explicit.group(0), " ", 1))
        return count, cleaned

    match = _COUNT_PATTERN.search(query)
    if match and any(
        marker in query for marker in ("给我", "来", "发我", "推荐", "列出", "返回")
    ):
        count = int(match.group(1))
        cleaned = _normalize_spacing(query.replace(match.group(0), " ", 1))
        return count, cleaned

    chinese_match = _CHINESE_COUNT_PATTERN.search(query)
    if chinese_match and any(
        marker in query for marker in ("给我", "来", "发我", "推荐", "列出", "返回")
    ):
        chinese_count = _CHINESE_COUNT_MAP.get(chinese_match.group(1))
        if chinese_count is not None:
            cleaned = _normalize_spacing(query.replace(chinese_match.group(0), " ", 1))
            return chinese_count, cleaned

    return None, query


def _extract_sort_intent(query: str) -> tuple[str | None, str]:
    """Extract coarse sort intent such as recent/hot."""
    for keyword in _SORT_HOT_KEYWORDS:
        if keyword in query:
            cleaned = _normalize_spacing(query.replace(keyword, " ", 1))
            return "hot", cleaned

    for keyword in _SORT_RECENT_KEYWORDS:
        if keyword in query:
            cleaned = _normalize_spacing(query.replace(keyword, " ", 1))
            return "recent", cleaned

    return None, query


def parse_query_rules(query: str) -> ParsedQuery:
    """Rule-based query parsing (always executed, no LLM)."""
    raw = query.strip()
    normalized = raw.lower()

    # Step 1: Extract content type
    parsed_content_type, cleaned = _extract_content_type(normalized)

    # Step 2: Extract explicit control intents and strip them from term source
    time_intent, cleaned = _extract_time_intent(cleaned)
    exclude_terms, cleaned = _extract_exclude_terms(cleaned)
    limit_intent, cleaned = _extract_limit_intent(cleaned)
    sort_intent, cleaned = _extract_sort_intent(cleaned)
    cleaned = _strip_request_prefix(cleaned)
    if sort_intent is None and time_intent is not None:
        sort_intent = "recent"

    # Step 3: Extract must terms from cleaned query
    must_terms = _extract_terms(cleaned) if cleaned else []

    # Step 4: Synonym expansion for should_terms
    should_terms = _expand_synonyms(must_terms)

    # Step 5: Determine if LLM rerank is warranted
    need_llm_rerank = (
        len(raw) > 8
        or len(must_terms) >= 2
        or sort_intent is not None
        or time_intent is not None
        or bool(exclude_terms)
        or limit_intent is not None
    )

    # Step 6: Build embedding text
    query_embedding_text = cleaned if cleaned else normalized

    return ParsedQuery(
        raw_query=raw,
        normalized_query=normalized,
        parsed_content_type=parsed_content_type,
        must_terms=must_terms,
        should_terms=should_terms,
        query_embedding_text=query_embedding_text,
        need_llm_rerank=need_llm_rerank,
        llm_used=False,
        sort_intent=sort_intent,
        time_intent=time_intent,
        exclude_terms=exclude_terms,
        limit_intent=limit_intent,
    )


async def _llm_parse_query(query: str) -> dict | None:
    """Call LLM for query understanding. Returns parsed dict or None on failure."""
    from app.services.infrastructure.ai import _dashscope_compat

    prompt = (
        "你是一个营销素材搜索系统的查询理解模块。\n"
        "请分析用户的查询意图，输出以下 JSON 结构，不要输出其他内容：\n"
        "{\n"
        '  "normalized_query": "归一化后的检索表达",\n'
        '  "content_type": "video | image | null",\n'
        '  "must_terms": ["强约束词1", "强约束词2"],\n'
        '  "should_terms": ["软约束词1"],\n'
        '  "intent": "意图简述"\n'
        "}\n\n"
        f"用户输入：{query}"
    )

    try:
        response = await asyncio.wait_for(
            _dashscope_compat.chat.completions.create(
                model=settings.SEARCH_LLM_QUERY_PARSE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=512,
                extra_body={"enable_thinking": False},
            ),
            timeout=settings.SEARCH_LLM_QUERY_PARSE_TIMEOUT_S,
        )
        text = response.choices[0].message.content or ""
        result: dict = json.loads(text)  # type: ignore[assignment]
        return result
    except TimeoutError:
        logger.warning(
            "LLM query parse timed out query_fp=%s query_len=%d",
            fingerprint_text(query),
            len(query),
        )
        return None
    except Exception:
        logger.warning(
            "LLM query parse failed query_fp=%s query_len=%d",
            fingerprint_text(query),
            len(query),
            exc_info=True,
        )
        return None


def _should_use_llm(query: str, rule_result: ParsedQuery) -> bool:
    """Decide whether to invoke LLM for query understanding."""
    if not settings.SEARCH_ENABLE_LLM_QUERY_PARSE:
        return False
    if (
        rule_result.sort_intent is not None
        or rule_result.time_intent is not None
        or bool(rule_result.exclude_terms)
    ):
        return True
    if len(query) > 10:
        return True
    if len(rule_result.must_terms) > 2:
        return True
    return False


async def parse_query(query: str) -> ParsedQuery:
    """Parse query using rules, optionally enhanced by LLM."""
    rule_result = parse_query_rules(query)

    if not _should_use_llm(query, rule_result):
        return rule_result

    llm_result = await _llm_parse_query(query)
    if llm_result is None:
        return rule_result

    # Merge LLM result into rule result
    parsed_content_type = rule_result.parsed_content_type
    llm_content_type = llm_result.get("content_type")
    if llm_content_type and llm_content_type != "null":
        parsed_content_type = llm_content_type

    llm_must = llm_result.get("must_terms", [])
    llm_should = llm_result.get("should_terms", [])
    llm_normalized = llm_result.get("normalized_query", rule_result.normalized_query)

    # Combine rule and LLM terms, deduplicate
    combined_must = list(dict.fromkeys(rule_result.must_terms + llm_must))
    combined_should = list(dict.fromkeys(rule_result.should_terms + llm_should))

    return ParsedQuery(
        raw_query=rule_result.raw_query,
        normalized_query=llm_normalized,
        parsed_content_type=parsed_content_type,
        must_terms=combined_must,
        should_terms=combined_should,
        query_embedding_text=llm_normalized,
        need_llm_rerank=rule_result.need_llm_rerank,
        llm_used=True,
        sort_intent=rule_result.sort_intent,
        time_intent=rule_result.time_intent,
        exclude_terms=rule_result.exclude_terms,
        limit_intent=rule_result.limit_intent,
    )
