"""Feishu bot event handlers: notifications + NL query."""

from __future__ import annotations

import asyncio
import logging
import tempfile

import httpx

from app.services.infrastructure.feishu import send_text_to_chat

logger = logging.getLogger("promoflow.api")


# ---------------------------------------------------------------------------
# Group chat registry (bot added / removed events)
# ---------------------------------------------------------------------------


async def register_group_chat(chat_id: str, chat_name: str | None) -> None:
    """Persist a group chat the bot has been added to."""
    from app.db.session import AsyncSessionLocal
    from app.models.feishu_group_chat import FeishuGroupChat

    async with AsyncSessionLocal() as db:
        existing = await db.get(FeishuGroupChat, chat_id)
        if existing is None:
            db.add(FeishuGroupChat(chat_id=chat_id, chat_name=chat_name))
            await db.commit()
            logger.info(
                "Bot added to group chat: chat_id=%s name=%s", chat_id, chat_name
            )
        else:
            logger.info("Bot re-added to known group chat: chat_id=%s", chat_id)


async def unregister_group_chat(chat_id: str) -> None:
    """Remove a group chat when the bot is removed."""
    from app.db.session import AsyncSessionLocal
    from app.models.feishu_group_chat import FeishuGroupChat

    async with AsyncSessionLocal() as db:
        existing = await db.get(FeishuGroupChat, chat_id)
        if existing is not None:
            await db.delete(existing)
            await db.commit()
            logger.info("Bot removed from group chat: chat_id=%s", chat_id)


# ---------------------------------------------------------------------------
# Approval notification – broadcast to all registered group chats
# ---------------------------------------------------------------------------


async def notify_content_approved(content_id: int) -> None:
    """Broadcast a new-content announcement to all registered group chats."""
    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.domains.content import ContentType
    from app.models.feishu_group_chat import FeishuGroupChat
    from app.services.content.core import (
        _content_to_output,
        get_content_orm,
        render_group_approved_markdown,
    )
    from app.services.infrastructure.feishu import (
        send_file_to_chat_sync as _feishu_send_file_sync,
    )
    from app.services.infrastructure.feishu import (
        send_image_to_chat_sync as _feishu_send_image_sync,
    )
    from app.services.infrastructure.feishu import (
        send_interactive_card_to_chat,
    )
    from app.services.infrastructure.storage import get_public_url

    # Fetch all registered group chats
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(FeishuGroupChat))).scalars().all()
        chat_ids = [row.chat_id for row in rows]

    if not chat_ids:
        logger.info("notify_content_approved: no registered group chats, skipping")
        return

    # Fetch content details
    async with AsyncSessionLocal() as db:
        content_orm = await get_content_orm(db, content_id)
        content_output = _content_to_output(content_orm)
        file_url = content_orm.file_url or get_public_url(content_orm.file_key)
        file_name = content_orm.file_key.rsplit("/", 1)[-1]
        is_image = content_orm.content_type == ContentType.image

    announcement_markdown = render_group_approved_markdown(content_output)
    title = (content_output.title or "新营销素材").strip() or "新营销素材"

    def _stream_oss_to_chats(
        url: str,
        chat_id_list: list[str],
        fname: str,
        img: bool,
    ) -> None:
        """Stream file from OSS once, then send to each group chat."""
        with httpx.Client(timeout=120.0) as http:
            with http.stream("GET", url) as resp:
                resp.raise_for_status()
                with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as tmp:
                    for chunk in resp.iter_bytes(65536):
                        tmp.write(chunk)
                    for cid in chat_id_list:
                        tmp.seek(0)
                        if img:
                            _feishu_send_image_sync(cid, tmp, fname)
                        else:
                            _feishu_send_file_sync(cid, tmp, fname)

    # Send card announcement to all chats
    for chat_id in chat_ids:
        try:
            await send_interactive_card_to_chat(
                chat_id, f"🎉 新营销素材：{title}", announcement_markdown
            )
        except Exception:
            logger.exception(
                "Failed to send announcement card to chat_id=%s for content=%s",
                chat_id,
                content_id,
            )

    # Stream file once and broadcast to all chats
    try:
        await asyncio.to_thread(
            _stream_oss_to_chats, file_url, chat_ids, file_name, is_image
        )
    except Exception:
        logger.exception(
            "Failed to broadcast file to group chats for content=%s", content_id
        )


# ---------------------------------------------------------------------------
# NL message handler (RAG search)
# ---------------------------------------------------------------------------


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
