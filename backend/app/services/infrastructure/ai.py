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


class _AnalysisResponse(BaseModel):
    """LLM response schema for content analysis. Internal use only."""

    title: str = ""
    summary: str = ""
    keywords: list[str] = Field(default_factory=list)


class _AnalysisResult(TypedDict):
    title: str
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
        parsed = _AnalysisResponse.model_validate_json(text)
    except Exception:
        json_str = _extract_json(text)
        parsed = _AnalysisResponse.model_validate(json.loads(json_str))
    return cast(_AnalysisResult, parsed.model_dump())


def _empty_analysis_result() -> _AnalysisResult:
    return {"title": "", "summary": "", "keywords": []}


def _extract_response_text(response: Any) -> str:
    """Extract text content from DashScope multimodal response."""
    content = response.output.choices[0].message.content
    if isinstance(content, list) and content:
        first_item = content[0]
        if isinstance(first_item, dict):
            return str(first_item.get("text", ""))
    return ""


def _call_multimodal(file_url: str, content_type: str) -> _AnalysisResult:
    """Sync call to Qianwen multimodal model."""
    content_type_label = _CONTENT_TYPE_LABELS.get(content_type, "素材")
    prompt_text = render("content_analysis.j2", content_type_label=content_type_label)

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


async def analyze_content(file_url: str, content_type: str) -> _AnalysisResult:
    """
    Send media to Qianwen multimodal model for analysis (sync SDK wrapped).
    Uses JSON Mode to force structured output for content analysis.
    """
    return await run_in_threadpool(_call_multimodal, file_url, content_type)


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
