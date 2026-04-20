import json
from types import SimpleNamespace

import pytest

from app.bot.handlers import handle_message_event
from app.domains.content import (
    AiStatus,
    ContentOutput,
    ContentStatus,
    ContentType,
    SearchResultOutput,
)


def _build_search_result(
    *,
    content_id: int,
    content_type: ContentType,
    file_key: str,
    file_url: str,
    title: str,
) -> SearchResultOutput:
    return SearchResultOutput(
        content=ContentOutput(
            id=content_id,
            title=title,
            description="测试素材",
            tags=["开业"],
            content_type=content_type,
            status=ContentStatus.approved,
            file_key=file_key,
            file_url=file_url,
            file_size=1,
            media_width=1920,
            media_height=1080,
            view_count=10,
            download_count=5,
            ai_summary="测试摘要",
            ai_keywords=["门店开业"],
            ai_status=AiStatus.completed,
            ai_error=None,
            ai_processed_at=None,
            uploaded_by=1,
            uploaded_by_name="测试同学",
            category_id=1,
            category_name="开业素材",
            primary_category_name="视频素材",
            created_at="2026-04-18T13:34:28+08:00",
            updated_at="2026-04-18T13:34:28+08:00",
        ),
        final_score=0.99,
        lexical_score=0.88,
        semantic_score=0.91,
        matched_signals=["recent"],
        reranked=True,
    )


class _AsyncSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, chunk_size: int):
        assert chunk_size == 65536
        yield self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeHttpClient:
    def __init__(self, *, timeout: float):
        assert timeout == 120.0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def stream(self, method: str, url: str):
        assert method == "GET"
        return _FakeResponse(b"abc")


@pytest.mark.asyncio
async def test_handle_message_event_sends_text_then_related_files_to_user(
    monkeypatch: pytest.MonkeyPatch,
):
    events: list[tuple[str, str]] = []
    results = [
        _build_search_result(
            content_id=1,
            content_type=ContentType.image,
            file_key="uploads/opening-1.png",
            file_url="https://example.com/opening-1.png",
            title="门店开业海报",
        ),
        _build_search_result(
            content_id=2,
            content_type=ContentType.video,
            file_key="uploads/opening-2.mp4",
            file_url="https://example.com/opening-2.mp4",
            title="门店开业视频",
        ),
    ]

    async def fake_send_text(chat_id: str, text: str) -> None:
        assert chat_id == "oc_test_chat"
        events.append(("text", text))

    async def fake_search_contents(db: object, *, command) -> SimpleNamespace:
        assert command.query == "给我最新的门店开业视频"
        return SimpleNamespace(results=results)

    async def fake_generate_rag_response(query: str, context_docs: list[str]) -> str:
        assert query == "给我最新的门店开业视频"
        assert len(context_docs) == 2
        return "根据创建时间，我为您筛选到 2 条相关素材。"

    async def fake_send_file_to_user(content_id: int, *, feishu_open_id: str) -> None:
        assert feishu_open_id == "ou_test_user"
        events.append(("deliver", str(content_id)))

    monkeypatch.setattr("app.bot.handlers.send_text_to_chat", fake_send_text)
    monkeypatch.setattr(
        "app.services.search.search_contents",
        fake_search_contents,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.ai.generate_rag_response",
        fake_generate_rag_response,
    )
    monkeypatch.setattr(
        "app.services.content.core.send_file_to_user",
        fake_send_file_to_user,
    )

    await handle_message_event(
        {
            "sender": {"sender_id": {"open_id": "ou_test_user"}},
            "message": {
                "chat_id": "oc_test_chat",
                "chat_type": "p2p",
                "message_type": "text",
                "content": json.dumps({"text": "@_bot 给我最新的门店开业视频"}),
            },
        }
    )

    assert events[0][0] == "text"
    assert "逐个发送对应素材的说明与文件" in events[0][1]
    assert events[1:] == [
        ("deliver", "1"),
        ("deliver", "2"),
    ]


@pytest.mark.asyncio
async def test_handle_message_event_continues_when_one_file_send_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    events: list[tuple[str, str]] = []
    results = [
        _build_search_result(
            content_id=1,
            content_type=ContentType.image,
            file_key="uploads/opening-1.png",
            file_url="https://example.com/opening-1.png",
            title="门店开业海报",
        ),
        _build_search_result(
            content_id=2,
            content_type=ContentType.video,
            file_key="uploads/opening-2.mp4",
            file_url="https://example.com/opening-2.mp4",
            title="门店开业视频",
        ),
    ]

    async def fake_send_text(chat_id: str, text: str) -> None:
        events.append(("text", text))

    async def fake_search_contents(db: object, *, command) -> SimpleNamespace:
        return SimpleNamespace(results=results)

    async def fake_generate_rag_response(query: str, context_docs: list[str]) -> str:
        return "我为您找到 2 条素材。"

    async def fake_send_file_to_user(content_id: int, *, feishu_open_id: str) -> None:
        if content_id == 1:
            events.append(("deliver_failed", str(content_id)))
            raise RuntimeError("send failed")
        events.append(("deliver", str(content_id)))

    monkeypatch.setattr("app.bot.handlers.send_text_to_chat", fake_send_text)
    monkeypatch.setattr(
        "app.services.search.search_contents",
        fake_search_contents,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.ai.generate_rag_response",
        fake_generate_rag_response,
    )
    monkeypatch.setattr(
        "app.services.content.core.send_file_to_user",
        fake_send_file_to_user,
    )

    await handle_message_event(
        {
            "sender": {"sender_id": {"open_id": "ou_test_user"}},
            "message": {
                "chat_id": "oc_test_chat",
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps({"text": "给我最新的门店开业视频"}),
            },
        }
    )

    assert events[0][0] == "text"
    assert "通过私信逐个发送" in events[0][1]
    assert events[1:] == [
        ("deliver_failed", "1"),
        ("deliver", "2"),
    ]


def test_append_file_delivery_note_does_not_repeat_existing_notice() -> None:
    from app.bot.handlers import _append_file_delivery_note

    answer = (
        "已为您筛选出 2 个相关素材。\n\n"
        "系统会继续逐个发送对应素材的说明与文件，请用户注意查收。"
    )

    assert _append_file_delivery_note(answer) == answer


@pytest.mark.asyncio
async def test_handle_message_event_falls_back_when_sender_open_id_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    events: list[tuple[str, str]] = []
    results = [
        _build_search_result(
            content_id=1,
            content_type=ContentType.image,
            file_key="uploads/opening-1.png",
            file_url="https://example.com/opening-1.png",
            title="门店开业海报",
        )
    ]

    async def fake_send_text(chat_id: str, text: str) -> None:
        events.append(("text", text))

    async def fake_search_contents(db: object, *, command) -> SimpleNamespace:
        return SimpleNamespace(results=results)

    async def fake_generate_rag_response(query: str, context_docs: list[str]) -> str:
        return "我为您找到 1 条素材。"

    monkeypatch.setattr("app.bot.handlers.send_text_to_chat", fake_send_text)
    monkeypatch.setattr(
        "app.services.search.search_contents",
        fake_search_contents,
    )
    monkeypatch.setattr(
        "app.services.infrastructure.ai.generate_rag_response",
        fake_generate_rag_response,
    )

    await handle_message_event(
        {
            "message": {
                "chat_id": "oc_test_chat",
                "chat_type": "group",
                "message_type": "text",
                "content": json.dumps({"text": "给我最新的门店开业视频"}),
            }
        }
    )

    assert events == [
        (
            "text",
            "我为您找到 1 条素材。\n\n---\n"
            "我会继续通过私信逐个发送对应素材的说明与文件，请注意查收。",
        ),
        (
            "text",
            "当前无法识别您的私信身份，暂时不能逐个发送素材说明与文件，请稍后重试。",
        ),
    ]
