"""Feishu bot event handlers: notifications + NL query."""

from __future__ import annotations

import httpx

from app.services.auth import get_feishu_app_token


async def _send_feishu_message(chat_id: str, text: str) -> None:
    """Send a text message to a Feishu group chat."""
    token = await get_feishu_app_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": f'{{"text": "{text}"}}',
            },
        )


async def notify_content_approved(content_id: int) -> None:
    """Push approval notification to configured group chat."""
    # In production, configure a default group chat_id via settings or DB
    pass


async def handle_message_event(event: dict) -> None:
    """Handle @bot message events and respond with RAG search results."""
    message = event.get("message", {})
    chat_id = message.get("chat_id", "")
    msg_type = message.get("message_type", "")

    if msg_type != "text":
        return

    import json as _json

    content_str = message.get("content", "{}")
    text = _json.loads(content_str).get("text", "").strip()

    # Remove @bot mention prefix if present
    if "@" in text:
        text = text.split(" ", 1)[-1].strip()

    if not text:
        return

    # Perform RAG search and reply
    from app.db.session import AsyncSessionLocal
    from app.domains.content import SearchContentCommand
    from app.services.infrastructure.ai import generate_embedding, generate_rag_response
    from app.services.search import semantic_search

    embedding = await generate_embedding(text)
    command = SearchContentCommand(query=text, limit=3)
    async with AsyncSessionLocal() as db:
        results = await semantic_search(db, query_embedding=embedding, command=command)

    if not results:
        await _send_feishu_message(chat_id, "暂未找到相关素材，请尝试其他关键词。")
        return

    context_docs = [
        f"{r.content.title}: {r.content.ai_summary or r.content.description or ''}"
        for r in results
    ]
    answer = await generate_rag_response(text, context_docs)
    await _send_feishu_message(chat_id, answer)
