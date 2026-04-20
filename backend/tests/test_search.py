import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    ParsedQuery,
    SearchContentCommand,
    SearchTimingOutput,
    UserRole,
)
from app.main import app
from app.models.category import Category
from app.models.content import Content
from app.models.user import User
from app.services.infrastructure.storage import get_public_url
from app.services.search.core_unified import _log_timing, search_contents
from app.services.search.query_parser import parse_query_rules
from app.services.search.ranker import compute_business_score
from app.services.search.retriever import RecallItem, _recall_fts_zhparser
from tests.conftest import TEST_PREFIX

_RUN = uuid.uuid4().hex[:8]


def _n(name: str) -> str:
    return f"{TEST_PREFIX}{_RUN}_{name}"


@pytest_asyncio.fixture
async def employee_user(db: AsyncSession) -> User:
    user = User(
        feishu_open_id=_n(f"emp_{uuid.uuid4().hex[:4]}"),
        feishu_union_id=_n(f"union_{uuid.uuid4().hex[:4]}"),
        name="测试员工",
        role=UserRole.employee,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def employee_client(
    client: AsyncClient,
    employee_user: User,
) -> AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: employee_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def category(db: AsyncSession) -> Category:
    category = Category(
        name=_n(f"类目_{uuid.uuid4().hex[:4]}"),
        description="测试类目",
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest.mark.asyncio
async def test_semantic_search_route_returns_results(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    content = Content(
        title=_n("促销海报"),
        description="夏季促销活动海报",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("search.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=[0.1] * 1024,
        ai_keywords=[],
    )
    db.add(content)
    await db.commit()

    async def fake_generate_embedding(query: str) -> list[float]:
        return [0.1] * 1024

    monkeypatch.setattr(
        "app.services.search.core_unified.generate_embedding",
        fake_generate_embedding,
    )

    resp = await employee_client.post(
        "/api/v1/search",
        json={"query": "夏季促销", "limit": 10},
    )

    assert resp.status_code == 200
    data = resp.json()
    results = data["results"]
    assert len(results) >= 1
    ids = [r["content"]["id"] for r in results]
    assert content.id in ids
    matched = next(
        result for result in results if result["content"]["id"] == content.id
    )
    assert matched["content"]["file_url"] == get_public_url(content.file_key)


@pytest.mark.asyncio
async def test_semantic_search_orders_by_similarity(
    employee_client: AsyncClient,
    db: AsyncSession,
    employee_user: User,
    category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    """Different query embeddings should produce different result orderings."""
    # Create two contents with distinct embeddings
    emb_a = [1.0] + [0.0] * 1023
    emb_b = [0.0] + [1.0] + [0.0] * 1022

    content_a = Content(
        title=_n("素材A"),
        description="A",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("a.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_a,
        ai_keywords=[],
    )
    content_b = Content(
        title=_n("素材B"),
        description="B",
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key=_n("b.png"),
        uploaded_by=employee_user.id,
        category_id=category.id,
        embedding=emb_b,
        ai_keywords=[],
    )
    db.add_all([content_a, content_b])
    await db.commit()

    # Query with embedding close to A → A should rank first
    async def fake_embedding_close_to_a(query: str) -> list[float]:
        return [0.9] + [0.1] + [0.0] * 1022

    monkeypatch.setattr(
        "app.services.search.core_unified.generate_embedding",
        fake_embedding_close_to_a,
    )
    resp1 = await employee_client.post(
        "/api/v1/search", json={"query": "查询A", "limit": 10}
    )
    assert resp1.status_code == 200
    ids_1 = [r["content"]["id"] for r in resp1.json()["results"]]

    # Query with embedding close to B → B should rank first
    async def fake_embedding_close_to_b(query: str) -> list[float]:
        return [0.1] + [0.9] + [0.0] * 1022

    monkeypatch.setattr(
        "app.services.search.core_unified.generate_embedding",
        fake_embedding_close_to_b,
    )
    resp2 = await employee_client.post(
        "/api/v1/search", json={"query": "查询B", "limit": 10}
    )
    assert resp2.status_code == 200
    ids_2 = [r["content"]["id"] for r in resp2.json()["results"]]

    # The two queries must produce different orderings
    assert ids_1 != ids_2
    assert ids_1[0] == content_a.id
    assert ids_2[0] == content_b.id


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


def test_recent_sort_intent_boosts_fresh_content() -> None:
    parsed = ParsedQuery(
        raw_query="给我最新的门店开业视频",
        normalized_query="给我最新的门店开业视频",
        parsed_content_type="video",
        must_terms=["门店开业"],
        should_terms=[],
        query_embedding_text="门店开业",
        need_llm_rerank=True,
        llm_used=False,
        sort_intent="recent",
        time_intent={"type": "relative_days", "days": 30, "label": "最近一个月"},
        exclude_terms=[],
        limit_intent=3,
    )

    fresh = ContentOutput(
        id=1,
        title="新门店开业视频",
        description="门店开业现场",
        tags=["门店", "开业"],
        content_type=ContentType.video,
        status=ContentStatus.approved,
        file_key="fresh.mp4",
        file_url="https://example.com/fresh.mp4",
        file_size=1,
        media_width=1920,
        media_height=1080,
        view_count=10,
        download_count=5,
        ai_summary="最新开业视频",
        ai_keywords=["门店开业"],
        ai_status=AiStatus.completed,
        ai_error=None,
        ai_processed_at=None,
        uploaded_by=1,
        uploaded_by_name="tester",
        category_id=1,
        category_name="门店素材",
        primary_category_name="开业",
        created_at="2026-04-10T00:00:00+00:00",
        updated_at="2026-04-10T00:00:00+00:00",
    )
    stale = ContentOutput(
        id=2,
        title="老门店开业视频",
        description="门店开业现场",
        tags=["门店", "开业"],
        content_type=ContentType.video,
        status=ContentStatus.approved,
        file_key="stale.mp4",
        file_url="https://example.com/stale.mp4",
        file_size=1,
        media_width=1920,
        media_height=1080,
        view_count=10,
        download_count=5,
        ai_summary="较早开业视频",
        ai_keywords=["门店开业"],
        ai_status=AiStatus.completed,
        ai_error=None,
        ai_processed_at=None,
        uploaded_by=1,
        uploaded_by_name="tester",
        category_id=1,
        category_name="门店素材",
        primary_category_name="开业",
        created_at="2025-12-01T00:00:00+00:00",
        updated_at="2025-12-01T00:00:00+00:00",
    )

    fresh_score, fresh_signals = compute_business_score(
        fresh,
        parsed,
        fts_rank=1.0,
        max_fts_rank=1.0,
        vector_similarity=1.0,
    )
    stale_score, stale_signals = compute_business_score(
        stale,
        parsed,
        fts_rank=1.0,
        max_fts_rank=1.0,
        vector_similarity=1.0,
    )

    assert fresh_score > stale_score
    assert any(signal.startswith("sort_recent:") for signal in fresh_signals)
    assert "time_window_miss:30d" in stale_signals


def test_search_timing_is_logged_even_when_debug_timing_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.search.core_unified.settings.SEARCH_DEBUG_TIMING",
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

    monkeypatch.setattr("app.services.search.core_unified.logger.info", fake_info)

    _log_timing(timing)

    assert logged_messages
    payload = json.loads(logged_messages[0])
    assert payload["message"] == "search_timing"


@pytest.mark.asyncio
async def test_search_contents_uses_query_limit_for_final_output_only(
    db: AsyncSession,
    employee_user: User,
    category: Category,
    monkeypatch: pytest.MonkeyPatch,
):
    contents: list[Content] = []
    for idx in range(6):
        content = Content(
            title=_n(f"门店开业视频{idx}"),
            description="门店开业现场视频",
            content_type=ContentType.video,
            status=ContentStatus.approved,
            file_key=_n(f"opening_{idx}.mp4"),
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

    seen = {}

    async def fake_rerank(candidates, parsed: ParsedQuery):
        seen["candidate_count"] = len(candidates)
        seen["limit_intent"] = parsed.limit_intent
        return [candidate[0].id for candidate in candidates]

    monkeypatch.setattr(
        "app.services.search.core_unified.generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_vector",
        fake_recall_vector,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_fts",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_tags",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.rerank_with_llm",
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
    monkeypatch: pytest.MonkeyPatch,
):
    contents: list[Content] = []
    for idx in range(5):
        content = Content(
            title=_n(f"食品素材{idx}"),
            description="食品推广图片",
            content_type=ContentType.image,
            status=ContentStatus.approved,
            file_key=_n(f"food_{idx}.png"),
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
        "app.services.search.core_unified.generate_embedding",
        fake_generate_embedding,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_vector",
        fake_recall_vector,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_fts",
        fake_empty_recall,
    )
    monkeypatch.setattr(
        "app.services.search.core_unified.recall_tags",
        fake_empty_recall,
    )

    async def fake_rerank_with_llm(candidates, parsed: ParsedQuery):
        return None

    monkeypatch.setattr(
        "app.services.search.core_unified.rerank_with_llm",
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
