"""Query understanding: rule-based parsing + optional LLM enhancement."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from app.core.config import settings
from app.domains.content import ParsedQuery
from app.services.search.dictionaries.content_type import CONTENT_TYPE_KEYWORD_MAP
from app.services.search.dictionaries.stopwords import STOPWORDS
from app.services.search.dictionaries.synonyms import SYNONYM_DICT

logger = logging.getLogger(__name__)

# CJK Unicode ranges for segmentation
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+")
_ALPHA_NUM_PATTERN = re.compile(r"[a-zA-Z0-9]+")


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


def parse_query_rules(query: str) -> ParsedQuery:
    """Rule-based query parsing (always executed, no LLM)."""
    raw = query.strip()
    normalized = raw.lower()

    # Step 1: Extract content type
    parsed_content_type, cleaned = _extract_content_type(normalized)

    # Step 2: Extract must terms from cleaned query
    must_terms = _extract_terms(cleaned) if cleaned else _extract_terms(normalized)

    # Step 3: Synonym expansion for should_terms
    should_terms = _expand_synonyms(must_terms)

    # Step 4: Determine if LLM rerank is warranted
    need_llm_rerank = len(raw) > 8 or len(must_terms) >= 2

    # Step 5: Build embedding text (use normalized query, not cleaned)
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
                max_tokens=256,
            ),
            timeout=settings.SEARCH_LLM_QUERY_PARSE_TIMEOUT_S,
        )
        text = response.choices[0].message.content or ""
        result: dict = json.loads(text)  # type: ignore[assignment]
        return result
    except TimeoutError:
        logger.warning("LLM query parse timed out for query: %s", query)
        return None
    except Exception:
        logger.warning("LLM query parse failed for query: %s", query, exc_info=True)
        return None


def _should_use_llm(query: str, rule_result: ParsedQuery) -> bool:
    """Decide whether to invoke LLM for query understanding."""
    if not settings.SEARCH_ENABLE_LLM_QUERY_PARSE:
        return False
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
    )
