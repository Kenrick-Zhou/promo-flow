import pytest

from app.services.search.query_parser import parse_query, parse_query_rules


def test_parse_query_rules_extracts_control_intents() -> None:
    parsed = parse_query_rules("给我3个最近一个月的门店开业视频，不要图片")

    assert parsed.parsed_content_type == "video"
    assert parsed.sort_intent == "recent"
    assert parsed.limit_intent == 3
    assert parsed.time_intent == {
        "type": "relative_days",
        "days": 30,
        "label": "最近一个月",
    }
    assert parsed.exclude_terms == ["图片"]
    assert "门店开业" in parsed.must_terms


def test_parse_query_rules_extracts_chinese_limit_intent() -> None:
    parsed = parse_query_rules("给我两个与食品相关的营销素材，最好是比较热门的")

    assert parsed.limit_intent == 2
    assert parsed.sort_intent == "hot"
    assert "食品" in parsed.query_embedding_text


@pytest.mark.asyncio
async def test_parse_query_prefers_llm_terms_over_rule_bigrams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.search.query_parser.settings.SEARCH_ENABLE_LLM_QUERY_PARSE",
        True,
        raising=False,
    )

    async def fake_llm_parse(query: str) -> dict[str, object]:
        return {
            "normalized_query": "食品营销素材 热门",
            "content_type": None,
            "must_terms": ["食品", "营销素材"],
            "should_terms": ["热门"],
            "intent": "找热门食品营销素材",
        }

    monkeypatch.setattr(
        "app.services.search.query_parser._llm_parse_query",
        fake_llm_parse,
    )

    parsed = await parse_query("给我两个与食品相关的营销素材，最好是比较热门的")

    assert parsed.llm_used is True
    assert parsed.must_terms == ["食品", "营销素材"]
    assert parsed.should_terms == ["热门"]
    assert "品相" not in parsed.must_terms


@pytest.mark.asyncio
async def test_parse_query_keeps_rule_controls_when_llm_supplies_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.search.query_parser.settings.SEARCH_ENABLE_LLM_QUERY_PARSE",
        True,
        raising=False,
    )

    async def fake_llm_parse(query: str) -> dict[str, object]:
        return {
            "normalized_query": "门店开业 热门素材",
            "content_type": "video",
            "must_terms": ["门店开业"],
            "should_terms": ["热门素材"],
            "intent": "找最近的门店开业视频",
        }

    monkeypatch.setattr(
        "app.services.search.query_parser._llm_parse_query",
        fake_llm_parse,
    )

    parsed = await parse_query("给我3个最近一个月的门店开业视频，不要图片")

    assert parsed.llm_used is True
    assert parsed.parsed_content_type == "video"
    assert parsed.must_terms == ["门店开业"]
    assert parsed.should_terms == ["热门素材"]
    assert parsed.limit_intent == 3
    assert parsed.sort_intent == "recent"
    assert parsed.time_intent == {
        "type": "relative_days",
        "days": 30,
        "label": "最近一个月",
    }
    assert parsed.exclude_terms == ["图片"]
