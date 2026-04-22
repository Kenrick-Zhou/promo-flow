"""Feishu bot event handlers: notifications + NL query."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
import time
from collections.abc import Sequence
from typing import Any

import httpx

from app.core.logging import fingerprint_text, mask_identifier
from app.domains.content import SearchResultOutput
from app.services.infrastructure.feishu import send_text_to_chat

logger = logging.getLogger("promoflow.api")

_FILE_DELIVERY_NOTE = "我会继续逐个发送对应素材的说明与文件，请注意查收。"
_GROUP_FILE_DELIVERY_NOTE = (
    "我会继续在当前群内逐个发送对应素材的说明与文件，请注意查收。"
)
_AT_TAG_PATTERN = re.compile(r"<at\b[^>]*>.*?</at>", re.IGNORECASE | re.DOTALL)
_INLINE_MENTION_PATTERN = re.compile(r"@_[^\s]+")


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
                "Bot added to group chat: chat_id=%s name=%s",
                mask_identifier(chat_id),
                chat_name,
            )
        else:
            logger.info(
                "Bot re-added to known group chat: chat_id=%s",
                mask_identifier(chat_id),
            )


async def unregister_group_chat(chat_id: str) -> None:
    """Remove a group chat when the bot is removed."""
    from app.db.session import AsyncSessionLocal
    from app.models.feishu_group_chat import FeishuGroupChat

    async with AsyncSessionLocal() as db:
        existing = await db.get(FeishuGroupChat, chat_id)
        if existing is not None:
            await db.delete(existing)
            await db.commit()
            logger.info(
                "Bot removed from group chat: chat_id=%s", mask_identifier(chat_id)
            )


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


def _normalize_message_text(text: str) -> str:
    """Strip bot mention placeholders and normalize whitespace."""
    normalized = _AT_TAG_PATTERN.sub(" ", text)
    normalized = _INLINE_MENTION_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("\u00a0", " ")
    return " ".join(normalized.split()).strip()


def _extract_post_text(content: dict[str, Any]) -> str:
    """Extract plain text from Feishu post message content."""
    for locale_payload in content.values():
        if not isinstance(locale_payload, dict):
            continue
        blocks = locale_payload.get("content")
        if not isinstance(blocks, list):
            continue

        parts: list[str] = []
        for block in blocks:
            if not isinstance(block, list):
                continue
            for element in block:
                if not isinstance(element, dict):
                    continue
                tag = element.get("tag")
                if tag == "text":
                    text = element.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        extracted = " ".join(part.strip() for part in parts if part.strip())
        if extracted:
            return extracted
    return ""


def _extract_message_text(message: dict[str, Any]) -> str:
    """Extract user query text from Feishu text/post message payloads."""
    msg_type = message.get("message_type", "")
    content_str = message.get("content", "{}")
    try:
        content = json.loads(content_str)
    except json.JSONDecodeError:
        logger.warning("bot_message_invalid_json content=%s", content_str)
        return ""

    raw_text = ""
    if msg_type == "text":
        text = content.get("text")
        raw_text = text if isinstance(text, str) else ""
    elif msg_type == "post":
        raw_text = _extract_post_text(content)

    return _normalize_message_text(raw_text)


def _append_file_delivery_note(answer: str) -> str:
    """Ensure the bot reply explicitly mentions follow-up file delivery."""
    stripped = answer.strip()
    if not stripped:
        return _FILE_DELIVERY_NOTE
    normalized = stripped.replace("素材文件", "文件").replace("当前会话", "")
    if _FILE_DELIVERY_NOTE in stripped or all(
        phrase in normalized for phrase in ("发送", "查收")
    ):
        return stripped
    return f"{stripped}\n\n---\n{_FILE_DELIVERY_NOTE}"


def _resolve_file_delivery_note(chat_type: str | None) -> str:
    """Build the user-facing file delivery note for the current chat scene."""
    if chat_type == "group":
        return _GROUP_FILE_DELIVERY_NOTE
    return _FILE_DELIVERY_NOTE


async def _send_related_files_to_user(
    feishu_open_id: str,
    results: Sequence[SearchResultOutput],
) -> None:
    """Reuse the user download flow so each file is preceded by its intro card."""
    from app.services.content.core import send_file_to_user

    for result in results:
        content_id = result.content.id
        logger.info(
            "bot_related_file_prepare open_id=%s content_id=%s",
            mask_identifier(feishu_open_id),
            content_id,
        )
        try:
            await send_file_to_user(content_id, feishu_open_id=feishu_open_id)
        except Exception:
            logger.exception(
                "Failed to send related file to open_id=%s content_id=%s",
                mask_identifier(feishu_open_id),
                content_id,
            )


async def _send_related_files_to_chat(
    chat_id: str,
    results: Sequence[SearchResultOutput],
) -> None:
    """Send each related material to the current group chat with intro + file."""
    from app.services.content.core import send_file_to_chat

    if not results:
        return

    logger.info(
        "bot_related_files_start chat_id=%s file_count=%d",
        mask_identifier(chat_id),
        len(results),
    )
    for result in results:
        content_id = result.content.id
        logger.info(
            "bot_related_file_prepare chat_id=%s content_id=%s",
            mask_identifier(chat_id),
            content_id,
        )
        try:
            await send_file_to_chat(content_id, chat_id=chat_id)
        except Exception:
            logger.exception(
                "Failed to send related file to chat_id=%s content_id=%s",
                mask_identifier(chat_id),
                content_id,
            )


async def handle_message_event(event: dict) -> None:
    """Handle @bot message events and respond with RAG search results."""
    total_start = time.monotonic()
    message = event.get("message", {})
    sender = event.get("sender", {})
    chat_id = message.get("chat_id", "")
    chat_type = message.get("chat_type")
    msg_type = message.get("message_type", "")
    sender_open_id = (
        sender.get("sender_id", {}).get("open_id") if isinstance(sender, dict) else None
    )

    if msg_type not in {"text", "post"}:
        return

    text = _extract_message_text(message)

    if not text:
        return

    logger.info(
        "bot_message_received chat_id=%s message_type=%s text_fp=%s text_len=%d",
        mask_identifier(chat_id),
        msg_type,
        fingerprint_text(text),
        len(text),
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
        mask_identifier(chat_id),
        len(result.results),
        (time.monotonic() - search_start) * 1000,
    )

    if not result.results:
        await send_text_to_chat(chat_id, "暂未找到相关素材，请尝试其他关键词。")
        logger.info(
            "bot_reply_sent chat_id=%s results=0 total_ms=%.1f",
            mask_identifier(chat_id),
            (time.monotonic() - total_start) * 1000,
        )
        return

    context_docs = [_build_context_doc(r) for r in result.results]
    rag_start = time.monotonic()
    answer = await generate_rag_response(text, context_docs)
    answer = _append_file_delivery_note(answer).replace(
        _FILE_DELIVERY_NOTE,
        _resolve_file_delivery_note(chat_type),
    )
    logger.info(
        "bot_answer_ready chat_id=%s duration_ms=%.1f",
        mask_identifier(chat_id),
        (time.monotonic() - rag_start) * 1000,
    )
    send_start = time.monotonic()
    await send_text_to_chat(chat_id, answer)
    if chat_type == "group":
        await _send_related_files_to_chat(chat_id, result.results)
    elif sender_open_id:
        await _send_related_files_to_user(sender_open_id, result.results)
    else:
        logger.warning(
            "bot_reply_skip_file_delivery chat_id=%s reason=missing_sender_open_id",
            mask_identifier(chat_id),
        )
    logger.info(
        "bot_reply_sent chat_id=%s answer_len=%d send_ms=%.1f total_ms=%.1f",
        mask_identifier(chat_id),
        len(answer),
        (time.monotonic() - send_start) * 1000,
        (time.monotonic() - total_start) * 1000,
    )
