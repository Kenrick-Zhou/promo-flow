import json
from types import SimpleNamespace

import pytest

from app.services.infrastructure import ai


def _make_multimodal_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(
        output=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=[{"text": text}]))]
        )
    )


@pytest.mark.asyncio
async def test_analyze_content_uses_json_mode_for_image(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    def fake_call(*, model: str, messages: list[dict[str, object]], **kwargs: object):
        captured["model"] = model
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return _make_multimodal_response(
            json.dumps(
                {
                    "title": "有方大健康产品海报",
                    "summary": "突出产品卖点与目标人群的营销海报。",
                    "keywords": ["大健康", "海报", "产品卖点"],
                },
                ensure_ascii=False,
            )
        )

    monkeypatch.setattr(ai, "render", lambda template, **kwargs: "prompt")
    monkeypatch.setattr(ai.MultiModalConversation, "call", fake_call)

    result = await ai.analyze_content("https://example.com/demo.png", "image")

    assert result == {
        "title": "有方大健康产品海报",
        "summary": "突出产品卖点与目标人群的营销海报。",
        "keywords": ["大健康", "海报", "产品卖点"],
    }
    assert captured["model"] == ai.settings.DASHSCOPE_VISION_MODEL
    assert captured["kwargs"] == {
        "response_format": {"type": "json_object"},
        "request_timeout": ai.MULTIMODAL_REQUEST_TIMEOUT,
    }

    messages = captured["messages"]
    assert isinstance(messages, list)
    assert messages[0]["content"][1] == {
        "type": "image",
        "image": "https://example.com/demo.png",
    }


@pytest.mark.asyncio
async def test_analyze_content_returns_empty_result_when_response_invalid(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_call(*, model: str, messages: list[dict[str, object]], **kwargs: object):
        return _make_multimodal_response("not-json")

    monkeypatch.setattr(ai, "render", lambda template, **kwargs: "prompt")
    monkeypatch.setattr(ai.MultiModalConversation, "call", fake_call)

    result = await ai.analyze_content("https://example.com/demo.mp4", "video")

    assert result == {
        "title": "",
        "summary": "",
        "keywords": [],
    }
