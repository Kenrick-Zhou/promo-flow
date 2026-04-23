from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    ParsedQuery,
)
from app.services.search.ranker import compute_business_score


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


def test_hot_sort_intent_uses_hot_score_deterministically() -> None:
    parsed = ParsedQuery(
        raw_query="给我热门食品素材",
        normalized_query="给我热门食品素材",
        parsed_content_type="image",
        must_terms=["食品"],
        should_terms=[],
        query_embedding_text="食品",
        need_llm_rerank=True,
        llm_used=True,
        sort_intent="hot",
    )

    hotter = ContentOutput(
        id=1,
        title="热门食品图",
        description="食品营销图",
        tags=["食品"],
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key="hot.png",
        file_url="https://example.com/hot.png",
        file_size=1,
        media_width=1080,
        media_height=1080,
        view_count=300,
        download_count=80,
        ai_summary="热门食品营销素材",
        ai_keywords=["食品"],
        ai_status=AiStatus.completed,
        ai_error=None,
        ai_processed_at=None,
        uploaded_by=1,
        uploaded_by_name="tester",
        category_id=1,
        category_name="食品",
        primary_category_name="营销",
        created_at="2026-04-10T00:00:00+00:00",
        updated_at="2026-04-10T00:00:00+00:00",
    )
    cooler = ContentOutput(
        id=2,
        title="普通食品图",
        description="食品营销图",
        tags=["食品"],
        content_type=ContentType.image,
        status=ContentStatus.approved,
        file_key="cool.png",
        file_url="https://example.com/cool.png",
        file_size=1,
        media_width=1080,
        media_height=1080,
        view_count=20,
        download_count=3,
        ai_summary="食品营销素材",
        ai_keywords=["食品"],
        ai_status=AiStatus.completed,
        ai_error=None,
        ai_processed_at=None,
        uploaded_by=1,
        uploaded_by_name="tester",
        category_id=1,
        category_name="食品",
        primary_category_name="营销",
        created_at="2026-04-10T00:00:00+00:00",
        updated_at="2026-04-10T00:00:00+00:00",
    )

    hotter_score, hotter_signals = compute_business_score(
        hotter,
        parsed,
        fts_rank=1.0,
        max_fts_rank=1.0,
        vector_similarity=1.0,
        hot_score=6.0,
    )
    cooler_score, cooler_signals = compute_business_score(
        cooler,
        parsed,
        fts_rank=1.0,
        max_fts_rank=1.0,
        vector_similarity=1.0,
        hot_score=0.8,
    )

    assert hotter_score > cooler_score
    assert any(signal.startswith("sort_hot:") for signal in hotter_signals)
    assert any(signal.startswith("sort_hot:") for signal in cooler_signals)
