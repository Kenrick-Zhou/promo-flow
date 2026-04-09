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
                    "summary": "突出产品卖点与目标人群的营销海报。",
                    "keywords": ["大健康", "海报", "产品卖点"],
                },
                ensure_ascii=False,
            )
        )

    monkeypatch.setattr(
        ai,
        "render",
        lambda template, **kwargs: json.dumps(kwargs, ensure_ascii=False),
    )
    monkeypatch.setattr(ai.MultiModalConversation, "call", fake_call)

    result = await ai.analyze_content(
        "https://example.com/demo.png",
        "image",
        primary_category_name="营养健康",
        category_name="宣传海报",
        tags=["胶原蛋白", "女性营养"],
        description="主推产品核心卖点",
    )

    assert result == {
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
    assert json.loads(messages[0]["content"][0]["text"]) == {
        "content_type_label": "图片",
        "primary_category_name": "营养健康",
        "category_name": "宣传海报",
        "tags": ["胶原蛋白", "女性营养"],
        "description": "主推产品核心卖点",
    }
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
        "summary": "",
        "keywords": [],
    }


@pytest.mark.asyncio
async def test_generate_content_title_uses_summary_keywords_and_context(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, object] = {}

    async def fake_create(**kwargs: object):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {"title": "胶原蛋白焕亮海报"},
                            ensure_ascii=False,
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr(
        ai,
        "render",
        lambda template, **kwargs: json.dumps(kwargs, ensure_ascii=False),
    )
    monkeypatch.setattr(ai._dashscope_compat.chat.completions, "create", fake_create)

    title = await ai.generate_content_title(
        "image",
        primary_category_name="营养健康",
        category_name="宣传海报",
        tags=["胶原蛋白", "女性营养"],
        description="主推产品核心卖点",
        summary="突出胶原蛋白产品焕亮卖点与适用人群。",
        keywords=["胶原蛋白", "焕亮", "女性营养"],
    )

    assert title == "胶原蛋白焕亮海报"
    assert captured["model"] == ai.settings.DASHSCOPE_RAG_MODEL
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["max_tokens"] == 128
    assert captured["messages"] == [
        {
            "role": "user",
            "content": json.dumps(
                {
                    "content_type_label": "图片",
                    "primary_category_name": "营养健康",
                    "category_name": "宣传海报",
                    "tags": ["胶原蛋白", "女性营养"],
                    "description": "主推产品核心卖点",
                    "summary": "突出胶原蛋白产品焕亮卖点与适用人群。",
                    "keywords": ["胶原蛋白", "焕亮", "女性营养"],
                },
                ensure_ascii=False,
            ),
        }
    ]


@pytest.mark.asyncio
async def test_generate_content_title_returns_empty_string_when_response_invalid(
    monkeypatch: pytest.MonkeyPatch,
):
    async def fake_create(**kwargs: object):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))]
        )

    monkeypatch.setattr(ai, "render", lambda template, **kwargs: "prompt")
    monkeypatch.setattr(ai._dashscope_compat.chat.completions, "create", fake_create)

    title = await ai.generate_content_title(
        "video",
        summary="摘要",
        keywords=["关键词"],
    )

    assert title == ""
