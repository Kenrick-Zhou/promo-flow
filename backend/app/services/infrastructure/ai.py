"""AI analysis adapter: Qianwen multimodal + DashScope embeddings + RAG."""

from __future__ import annotations

import json

import dashscope
from dashscope import MultiModalConversation
from openai import AsyncOpenAI
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY

# DashScope OpenAI-compatible endpoint for embeddings and RAG chat
_dashscope_compat = AsyncOpenAI(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024


def _call_multimodal(file_url: str, content_type: str) -> dict:
    """Sync call to Qianwen multimodal model."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "请分析以下营销素材，输出一段简洁的摘要（100字以内）和5个关键词。"
                        '以JSON格式返回：{"summary": "...", "keywords": ["..."]}'
                    ),
                },
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
        result: dict[str, object] = json.loads(text)
        return result
    except Exception:
        return {"summary": "", "keywords": []}


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
    messages = [
        {
            "role": "system",
            "content": "你是一个营销素材助手，根据检索到的素材信息回答用户问题。",
        },
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
