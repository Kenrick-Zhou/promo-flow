"""AI analysis adapter: Qianwen multimodal + DashScope embeddings + RAG."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict, cast

import dashscope
from dashscope import MultiModalConversation
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.prompts import render

dashscope.api_key = settings.DASHSCOPE_API_KEY

# DashScope OpenAI-compatible endpoint for embeddings and RAG chat
_dashscope_compat = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024
MULTIMODAL_REQUEST_TIMEOUT = 300
_JSON_MODE_RESPONSE_FORMAT = {"type": "json_object"}

_CONTENT_TYPE_LABELS = {
    "image": "图片",
    "video": "视频",
    "document": "文档",
}


class _StructuredContext(TypedDict):
    """Structured business context supplied to the AI prompts."""

    primary_category_name: str | None
    category_name: str | None
    tags: list[str]
    description: str | None


class _SummaryKeywordsResponse(BaseModel):
    """LLM response schema for summary/keywords analysis. Internal use only."""

    summary: str = ""
    keywords: list[str] = Field(default_factory=list)


class _TitleResponse(BaseModel):
    """LLM response schema for generated title. Internal use only."""

    title: str = ""


class _AnalysisResult(TypedDict):
    summary: str
    keywords: list[str]


def _extract_json(text: str) -> str:
    """Extract JSON object from LLM response that may contain markdown fences."""
    # Try to find JSON inside ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    # Try to find bare JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _build_media_part(file_url: str, content_type: str) -> dict[str, str]:
    """Build DashScope multimodal content part for the given media type."""
    media_key = "image" if content_type == "image" else "video"
    return {
        "type": media_key,
        media_key: file_url,
    }


def _parse_analysis_text(text: str) -> _AnalysisResult:
    """Parse multimodal analysis response text into a validated result."""
    try:
        parsed = _SummaryKeywordsResponse.model_validate_json(text)
    except Exception:
        json_str = _extract_json(text)
        parsed = _SummaryKeywordsResponse.model_validate(json.loads(json_str))
    return cast(_AnalysisResult, parsed.model_dump())


def _parse_title_text(text: str) -> str:
    """Parse title generation response text into a validated title."""
    try:
        parsed = _TitleResponse.model_validate_json(text)
    except Exception:
        json_str = _extract_json(text)
        parsed = _TitleResponse.model_validate(json.loads(json_str))
    return parsed.title.strip()


def _empty_analysis_result() -> _AnalysisResult:
    return {"summary": "", "keywords": []}


def _normalize_context(
    *,
    primary_category_name: str | None,
    category_name: str | None,
    tags: list[str] | None,
    description: str | None,
) -> _StructuredContext:
    return {
        "primary_category_name": primary_category_name,
        "category_name": category_name,
        "tags": [tag.strip() for tag in (tags or []) if tag.strip()],
        "description": description.strip() if description else None,
    }


def _build_prompt_kwargs(
    *,
    content_type: str,
    primary_category_name: str | None,
    category_name: str | None,
    tags: list[str] | None,
    description: str | None,
) -> dict[str, object]:
    normalized = _normalize_context(
        primary_category_name=primary_category_name,
        category_name=category_name,
        tags=tags,
        description=description,
    )
    return {
        "content_type_label": _CONTENT_TYPE_LABELS.get(content_type, "素材"),
        "primary_category_name": normalized["primary_category_name"] or "未提供",
        "category_name": normalized["category_name"] or "未提供",
        "tags": normalized["tags"],
        "description": normalized["description"] or "未提供",
    }


def _extract_response_text(response: Any) -> str:
    """Extract text content from DashScope multimodal response."""
    content = response.output.choices[0].message.content
    if isinstance(content, list) and content:
        first_item = content[0]
        if isinstance(first_item, dict):
            return str(first_item.get("text", ""))
    return ""


def _call_multimodal(
    file_url: str,
    content_type: str,
    *,
    primary_category_name: str | None,
    category_name: str | None,
    tags: list[str] | None,
    description: str | None,
) -> _AnalysisResult:
    """Sync call to Qianwen multimodal model."""
    prompt_text = render(
        "content_analysis.j2",
        **_build_prompt_kwargs(
            content_type=content_type,
            primary_category_name=primary_category_name,
            category_name=category_name,
            tags=tags,
            description=description,
        ),
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                _build_media_part(file_url, content_type),
            ],
        }
    ]

    try:
        response = cast(
            Any,
            MultiModalConversation.call(
                model=settings.DASHSCOPE_VISION_MODEL,
                messages=messages,
                response_format=_JSON_MODE_RESPONSE_FORMAT,
                request_timeout=MULTIMODAL_REQUEST_TIMEOUT,
            ),
        )
        return _parse_analysis_text(_extract_response_text(response))
    except Exception:
        return _empty_analysis_result()


async def analyze_content(
    file_url: str,
    content_type: str,
    *,
    primary_category_name: str | None = None,
    category_name: str | None = None,
    tags: list[str] | None = None,
    description: str | None = None,
) -> _AnalysisResult:
    """
    Send media to Qianwen multimodal model for summary/keywords analysis.
    Uses JSON Mode to force structured output and includes upload metadata as context.
    """
    return await run_in_threadpool(
        _call_multimodal,
        file_url,
        content_type,
        primary_category_name=primary_category_name,
        category_name=category_name,
        tags=tags,
        description=description,
    )


async def generate_content_title(
    content_type: str,
    *,
    primary_category_name: str | None = None,
    category_name: str | None = None,
    tags: list[str] | None = None,
    description: str | None = None,
    summary: str,
    keywords: list[str],
) -> str:
    """Generate a content title after summary/keywords are produced."""
    prompt_text = render(
        "content_title.j2",
        **_build_prompt_kwargs(
            content_type=content_type,
            primary_category_name=primary_category_name,
            category_name=category_name,
            tags=tags,
            description=description,
        ),
        summary=summary or "未生成",
        keywords=keywords,
    )
    try:
        response = await _dashscope_compat.chat.completions.create(
            model=settings.DASHSCOPE_RAG_MODEL,
            messages=[{"role": "user", "content": prompt_text}],  # type: ignore[list-item]
            response_format=cast(Any, _JSON_MODE_RESPONSE_FORMAT),
            max_tokens=128,
        )
        return _parse_title_text(response.choices[0].message.content or "")
    except Exception:
        return ""


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector using DashScope text-embedding-v3."""
    response = await _dashscope_compat.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIM,
    )
    return response.data[0].embedding


async def generate_rag_response(query: str, context_docs: list[str]) -> str:
    """Generate a natural language response using retrieved contexts (RAG)."""
    context = "\n\n".join(f"[{i + 1}] {doc}" for i, doc in enumerate(context_docs))
    system_prompt = render("rag_system.j2")
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"相关素材信息：\n{context}\n\n用户问题：{query}",
        },
    ]
    response = await _dashscope_compat.chat.completions.create(
        model=settings.DASHSCOPE_RAG_MODEL,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=512,
    )
    return response.choices[0].message.content or ""
