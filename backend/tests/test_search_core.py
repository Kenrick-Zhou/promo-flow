import json
from collections.abc import Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content import (
    ParsedQuery,
    SearchContentCommand,
    SearchTimingOutput,
)
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from app.services.search.core import _log_timing, search_contents
from app.services.search.retriever import RecallItem


def test_search_timing_is_logged_even_when_debug_timing_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.search.core.settings.SEARCH_DEBUG_TIMING",
        False,
        raising=False,
    )

    timing = SearchTimingOutput(
        query_parse_ms=1.0,
        vector_recall_ms=2.0,
        fts_recall_ms=3.0,
        tag_recall_ms=4.0,
        rrf_merge_ms=5.0,
        scoring_ms=6.0,
        llm_rerank_ms=None,
        total_ms=7.0,
    )

    logged_messages: list[str] = []

    def fake_info(message: str) -> None:
        logged_messages.append(message)

    monkeypatch.setattr("app.services.search.core.logger.info", fake_info)

    parsed = ParsedQuery(
        raw_query="食品热门素材",
        normalized_query="食品热门素材",
        parsed_content_type="image",
        must_terms=["食品"],
        should_terms=["热门"],
        query_embedding_text="食品热门素材",
        need_llm_rerank=True,
        llm_used=True,
        sort_intent="hot",
        limit_intent=2,
    )

    _log_timing(
        timing,
        embedding_ms=0.5,
        parsed=parsed,
        vector_hits=5,
        fts_hits=4,
        tag_hits=2,
        candidate_count=6,
        result_count=2,
        reranked=True,
    )

    assert logged_messages
    payload = json.loads(logged_messages[0])
    assert payload["message"] == "search_timing"
    assert payload["llm_used"] is True
    assert payload["candidate_count"] == 6
    assert payload["result_count"] == 2
    assert payload["vector_hits"] == 5


@pytest.mark.asyncio
async def test_search_contents_uses_query_limit_for_final_output_only(
    db: AsyncSession,
    employee_user: User,
    category: Category,
    make_search_name: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
):
    contents: list[Content] = []
    for idx in range(6):
        content = Content(
            title=make_search_name(f"门店开业视频{idx}"),
            description="门店开业现场视频",
            content_type="video",
            status="approved",
            file_key=make_search_name(f"opening_{idx}.mp4"),
            uploaded_by=employee_user.id,
            category_id=category.id,
            embedding=[0.1] * 1024,
            ai_keywords=["开业", "门店"],
        )
        contents.append(content)
    db.add_all(contents)
    await db.commit()

    async def fake_generate_embedding(query: str) -> list[float]:
        return [0.1] * 1024

    async def fake_recall_vector(*args, **kwargs) -> list[RecallItem]:
        return [
            RecallItem(content_id=content.id, score=1.0 - idx * 0.01)
            for idx, content in enumerate(contents)
        ]

    async def fake_empty_recall(*args, **kwargs) -> list[RecallItem]:
        return []

    seen: dict[str, int] = {}

    async def fake_rerank(candidates, parsed: ParsedQuery):
        seen["candidate_count"] = len(candidates)
        seen["limit_intent"] = parsed.limit_intent or 0
        return [candidate[0].id for candidate in candidates]

    monkeypatch.setattr(
        "app.services.search.core.generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_vector",
        fake_recall_vector,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_fts",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_tags",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core.rerank_with_llm",
        fake_rerank,
    )

    result = await search_contents(
        db,
        command=SearchContentCommand(
            query="给我3个最近的门店开业视频",
            limit=5,
            allow_query_limit_override=True,
        ),
    )

    assert seen["candidate_count"] == 6
    assert seen["limit_intent"] == 3
    assert len(result.results) == 3


@pytest.mark.asyncio
async def test_search_contents_respects_chinese_query_limit_intent(
    db: AsyncSession,
    employee_user: User,
    category: Category,
    make_search_name: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
):
    contents: list[Content] = []
    for idx in range(5):
        content = Content(
            title=make_search_name(f"食品素材{idx}"),
            description="食品推广图片",
            content_type="image",
            status="approved",
            file_key=make_search_name(f"food_{idx}.png"),
            uploaded_by=employee_user.id,
            category_id=category.id,
            embedding=[0.1] * 1024,
            ai_keywords=["食品", "零食"],
            view_count=10 - idx,
            download_count=5 - idx,
        )
        contents.append(content)
    db.add_all(contents)
    await db.commit()

    async def fake_generate_embedding(query: str) -> list[float]:
        return [0.1] * 1024

    async def fake_recall_vector(*args, **kwargs) -> list[RecallItem]:
        return [
            RecallItem(content_id=content.id, score=1.0 - idx * 0.01)
            for idx, content in enumerate(contents)
        ]

    async def fake_empty_recall(*args, **kwargs) -> list[RecallItem]:
        return []

    monkeypatch.setattr(
        "app.services.search.core.generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_vector",
        fake_recall_vector,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_fts",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_tags",
        fake_empty_recall,
    )

    async def fake_rerank_with_llm(candidates, parsed: ParsedQuery):
        return None

    monkeypatch.setattr(
        "app.services.search.core.rerank_with_llm",
        fake_rerank_with_llm,
    )

    result = await search_contents(
        db,
        command=SearchContentCommand(
            query="给我两个与食品相关的营销素材，最好是比较热门的",
            limit=5,
            allow_query_limit_override=True,
        ),
    )

    assert len(result.results) == 2
    assert [item.content.id for item in result.results] == [
        contents[0].id,
        contents[1].id,
    ]


@pytest.mark.asyncio
async def test_search_contents_respects_llm_rerank_subset_without_readding_tail(
    db: AsyncSession,
    employee_user: User,
    category: Category,
    make_search_name: Callable[[str], str],
    monkeypatch: pytest.MonkeyPatch,
):
    contents: list[Content] = []
    for idx in range(5):
        content = Content(
            title=make_search_name(f"食品素材{idx}"),
            description="食品推广图片",
            content_type="image",
            status="approved",
            file_key=make_search_name(f"food_rerank_{idx}.png"),
            uploaded_by=employee_user.id,
            category_id=category.id,
            embedding=[0.1] * 1024,
            ai_keywords=["食品", "零食"],
            view_count=10 - idx,
            download_count=5 - idx,
        )
        contents.append(content)
    db.add_all(contents)
    await db.commit()

    async def fake_generate_embedding(query: str) -> list[float]:
        return [0.1] * 1024

    async def fake_recall_vector(*args, **kwargs) -> list[RecallItem]:
        return [
            RecallItem(content_id=content.id, score=1.0 - idx * 0.01)
            for idx, content in enumerate(contents)
        ]

    async def fake_empty_recall(*args, **kwargs) -> list[RecallItem]:
        return []

    async def fake_rerank(candidates, parsed: ParsedQuery):
        assert len(candidates) == 5
        return [contents[0].id, contents[2].id, contents[4].id]

    monkeypatch.setattr(
        "app.services.search.core.generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_vector",
        fake_recall_vector,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_fts",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core.recall_tags",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core.rerank_with_llm",
        fake_rerank,
    )

    result = await search_contents(
        db,
        command=SearchContentCommand(
            query="有没有吃的素材",
            limit=5,
            allow_query_limit_override=True,
        ),
    )

    assert [item.content.id for item in result.results] == [
        contents[0].id,
        contents[2].id,
        contents[4].id,
    ]
    assert len(result.results) == 3
    assert all(item.reranked for item in result.results)
