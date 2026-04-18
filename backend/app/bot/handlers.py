"""Feishu bot event handlers: notifications + NL query."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import time

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


def _build_context_doc(result) -> str:
    """Build rich RAG context for timestamps and ranking signals."""
    content = result.content
    matched_signals = (
        "、".join(result.matched_signals[:6]) if result.matched_signals else "无"
    )
    return (
        f"标题：{_build_context_title(content.title)}\n"
        f"类型：{content.content_type.value}\n"
        f"一级分类：{content.primary_category_name or '未提供'}\n"
        f"分类：{content.category_name or '未提供'}\n"
        f"创建时间：{content.created_at or '未提供'}\n"
        f"更新时间：{content.updated_at or '未提供'}\n"
        f"浏览量：{content.view_count}\n"
        f"下载量：{content.download_count}\n"
        f"标签：{'、'.join(content.tags[:8]) if content.tags else '无'}\n"
        f"关键词：{_join_keywords(content.ai_keywords)}\n"
        f"摘要：{content.ai_summary or content.description or '未提供'}\n"
        f"匹配信号：{matched_signals}\n"
        f"综合分：{result.final_score:.2f}"
    )


def _join_keywords(keywords: list[str]) -> str:
    """Format a compact keyword string for bot RAG context."""
    if not keywords:
        return "无"
    return "、".join(keywords[:8])


async def handle_message_event(event: dict) -> None:
    """Handle @bot message events and respond with RAG search results."""
    total_start = time.monotonic()
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

    logger.info(
        "bot_message_received chat_id=%s message_type=%s text=%s",
        chat_id,
        msg_type,
        text[:120],
    )

    # Perform unified search and reply
    from app.db.session import AsyncSessionLocal
    from app.domains.content import SearchContentCommand
    from app.services.infrastructure.ai import generate_rag_response
    from app.services.search import search_contents

    command = SearchContentCommand(
        query=text,
        limit=5,
        allow_query_limit_override=True,
    )
    search_start = time.monotonic()
    async with AsyncSessionLocal() as db:
        result = await search_contents(db, command=command)
    logger.info(
        "bot_search_done chat_id=%s results=%d duration_ms=%.1f",
        chat_id,
        len(result.results),
        (time.monotonic() - search_start) * 1000,
    )

    if not result.results:
        await send_text_to_chat(chat_id, "暂未找到相关素材，请尝试其他关键词。")
        logger.info(
            "bot_reply_sent chat_id=%s results=0 total_ms=%.1f",
            chat_id,
            (time.monotonic() - total_start) * 1000,
        )
        return

    context_docs = [_build_context_doc(r) for r in result.results]
    rag_start = time.monotonic()
    answer = await generate_rag_response(text, context_docs)
    logger.info(
        "bot_answer_ready chat_id=%s duration_ms=%.1f",
        chat_id,
        (time.monotonic() - rag_start) * 1000,
    )
    send_start = time.monotonic()
    await send_text_to_chat(chat_id, answer)
    logger.info(
        "bot_reply_sent chat_id=%s answer_len=%d send_ms=%.1f total_ms=%.1f",
        chat_id,
        len(answer),
        (time.monotonic() - send_start) * 1000,
        (time.monotonic() - total_start) * 1000,
    )
