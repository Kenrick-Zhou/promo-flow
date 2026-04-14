"""Feishu bot event handlers: notifications + NL query."""

from __future__ import annotations

from app.services.infrastructure.feishu import send_text_to_chat


async def notify_content_approved(content_id: int) -> None:
    """Push approval notification to configured group chat."""
    # In production, configure a default group chat_id via settings or DB
    pass


def _build_context_title(title: str | None) -> str:
    return title or "未命名素材"


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

    # Perform unified search and reply
    from app.db.session import AsyncSessionLocal
    from app.domains.content import SearchContentCommand
    from app.services.infrastructure.ai import generate_rag_response
    from app.services.search import search_contents

    command = SearchContentCommand(query=text, limit=5)
    async with AsyncSessionLocal() as db:
        result = await search_contents(db, command=command)

    if not result.results:
        await send_text_to_chat(chat_id, "暂未找到相关素材，请尝试其他关键词。")
        return

    context_docs = [
        (
            f"{_build_context_title(r.content.title)}: "
            f"{r.content.ai_summary or r.content.description or ''}"
        )
        for r in result.results
    ]
    answer = await generate_rag_response(text, context_docs)
    await send_text_to_chat(chat_id, answer)
