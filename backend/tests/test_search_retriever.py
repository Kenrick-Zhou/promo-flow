from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import DBAPIError

from app.domains.content import ParsedQuery
from app.services.search.retriever import (
    RecallItem,
    _recall_fts_zhparser,
    recall_fts,
    recall_tags,
)


@pytest.mark.asyncio
async def test_recall_fts_falls_back_to_ilike_when_zhparser_config_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    parsed = ParsedQuery(
        raw_query="礼炮",
        normalized_query="礼炮",
        parsed_content_type=None,
        must_terms=[],
        should_terms=["礼炮"],
        query_embedding_text="礼炮",
        need_llm_rerank=False,
        llm_used=False,
    )

    db = SimpleNamespace(
        rollback=AsyncMock(),
        execute=AsyncMock(
            side_effect=DBAPIError(
                statement="SELECT 1",
                params={},
                orig=RuntimeError(
                    'text search configuration "zhparser" does not exist'
                ),
            )
        ),
    )

    fallback_items = [RecallItem(content_id=123, score=1.0)]

    async def fake_ilike(*args, **kwargs):
        return fallback_items

    monkeypatch.setattr("app.services.search.retriever._recall_fts_ilike", fake_ilike)

    result = await _recall_fts_zhparser(db, query_text="礼炮", parsed=parsed)

    assert result == fallback_items


@pytest.mark.asyncio
async def test_recall_fts_raises_unrelated_db_errors(
    monkeypatch: pytest.MonkeyPatch,
):
    parsed = ParsedQuery(
        raw_query="礼炮",
        normalized_query="礼炮",
        parsed_content_type=None,
        must_terms=[],
        should_terms=["礼炮"],
        query_embedding_text="礼炮",
        need_llm_rerank=False,
        llm_used=False,
    )

    db = SimpleNamespace(
        rollback=AsyncMock(),
        execute=AsyncMock(
            side_effect=DBAPIError(
                statement="SELECT 1",
                params={},
                orig=RuntimeError("some other database error"),
            )
        ),
    )

    async def fake_ilike(*args, **kwargs):
        raise AssertionError("ILIKE fallback should not run for unrelated errors")

    monkeypatch.setattr("app.services.search.retriever._recall_fts_ilike", fake_ilike)

    with pytest.raises(DBAPIError):
        await _recall_fts_zhparser(db, query_text="礼炮", parsed=parsed)


@pytest.mark.asyncio
async def test_recall_fts_dispatches_to_ilike_backend_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parsed = ParsedQuery(
        raw_query="食品素材",
        normalized_query="食品素材",
        parsed_content_type=None,
        must_terms=["食品"],
        should_terms=["素材"],
        query_embedding_text="食品素材",
        need_llm_rerank=False,
        llm_used=False,
    )

    expected = [RecallItem(content_id=8, score=1.0)]

    async def fake_ilike(*args, **kwargs) -> list[RecallItem]:
        return expected

    monkeypatch.setattr(
        "app.services.search.retriever.settings.SEARCH_FTS_BACKEND",
        "ilike",
        raising=False,
    )
    monkeypatch.setattr("app.services.search.retriever._recall_fts_ilike", fake_ilike)

    result = await recall_fts(SimpleNamespace(), query_text="食品素材", parsed=parsed)

    assert result == expected


@pytest.mark.asyncio
async def test_recall_tags_uses_single_batched_query() -> None:
    rows = [
        SimpleNamespace(content_id=101, score=3.8),
        SimpleNamespace(content_id=102, score=2.5),
    ]
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: rows))
    )
    parsed = ParsedQuery(
        raw_query="食品营销素材",
        normalized_query="食品营销素材",
        parsed_content_type="image",
        must_terms=["食品", "营销素材"],
        should_terms=["热门"],
        query_embedding_text="食品营销素材",
        need_llm_rerank=True,
        llm_used=True,
        sort_intent="hot",
    )

    result = await recall_tags(db, parsed=parsed)

    assert db.execute.await_count == 1
    assert [item.content_id for item in result] == [101, 102]
    assert [item.score for item in result] == [3.8, 2.5]
