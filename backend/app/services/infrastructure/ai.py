"""AI analysis adapter: Qianwen multimodal + DashScope embeddings + RAG."""

from __future__ import annotations

import json
import re

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


def _call_multimodal(file_url: str, content_type: str) -> dict:
    """Sync call to Qianwen multimodal model."""
    content_type_label = _CONTENT_TYPE_LABELS.get(content_type, "素材")
    prompt_text = render("content_analysis.j2", content_type_label=content_type_label)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image" if content_type == "image" else "video",
                    "image": file_url,
                },
            ],
        }
    ]

    response = MultiModalConversation.call(
        model=settings.DASHSCOPE_VISION_MODEL,
        messages=messages,
    )

    try:
        text = response.output.choices[0].message.content[0]["text"]
        json_str = _extract_json(text)
        parsed = _AnalysisResponse.model_validate(json.loads(json_str))
        return parsed.model_dump()
    except Exception:
        return {"title": "", "summary": "", "keywords": []}


async def analyze_content(file_url: str, content_type: str) -> dict:
    """
    Send media to Qianwen multimodal model for analysis (sync SDK wrapped).
    Returns {"summary": str, "keywords": list[str]}.
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
