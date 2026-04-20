"""Feishu WebSocket long-connection client for receiving bot events."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger("promoflow.api")


def _make_event_handler(
    main_loop: asyncio.AbstractEventLoop,
) -> Any:
    import lark_oapi as lark

    from app.bot.handlers import (
        handle_message_event,
        register_group_chat,
        unregister_group_chat,
    )

    def do_bot_added(data: Any) -> None:
        if data.event is None:
            return
        chat_id = data.event.chat_id or ""
        chat_name = data.event.name
        if not chat_id:
            return
        fut = asyncio.run_coroutine_threadsafe(
            register_group_chat(chat_id, chat_name), main_loop
        )
        try:
            fut.result(timeout=5)
        except Exception:
            logger.exception("register_group_chat failed for chat_id=%s", chat_id)

    def do_bot_deleted(data: Any) -> None:
        if data.event is None:
            return
        chat_id = data.event.chat_id or ""
        if not chat_id:
            return
        fut = asyncio.run_coroutine_threadsafe(
            unregister_group_chat(chat_id), main_loop
        )
        try:
            fut.result(timeout=5)
        except Exception:
            logger.exception("unregister_group_chat failed for chat_id=%s", chat_id)

    def do_message_receive(data: Any) -> None:
        if data.event is None or data.event.message is None:
            return
        msg = data.event.message
        sender = getattr(data.event, "sender", None)
        sender_id = getattr(sender, "sender_id", None)
        # Reconstruct the dict format expected by handle_message_event
        event_dict = {
            "message": {
                "chat_id": msg.chat_id or "",
                "chat_type": getattr(msg, "chat_type", None),
                "message_type": msg.message_type or "",
                "content": msg.content or "{}",
            },
            "sender": {
                "sender_id": {
                    "open_id": getattr(sender_id, "open_id", None),
                }
            },
        }
        # Fire-and-forget: don't block the ws receive loop for potentially slow RAG
        asyncio.run_coroutine_threadsafe(handle_message_event(event_dict), main_loop)

    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_chat_member_bot_added_v1(do_bot_added)
        .register_p2_im_chat_member_bot_deleted_v1(do_bot_deleted)
        .register_p2_im_message_receive_v1(do_message_receive)
        .build()
    )


def start_ws_client(main_loop: asyncio.AbstractEventLoop) -> None:
    """Start the Feishu WebSocket long-connection client in a daemon thread."""

    def _run() -> None:
        # Create a fresh event loop for this thread BEFORE constructing the
        # SDK client, so that the SDK's module-level cached loop and internal
        # asyncio primitives bind to this loop instead of the main uvloop.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        import lark_oapi as lark

        event_handler = _make_event_handler(main_loop)
        cli = lark.ws.Client(
            settings.FEISHU_APP_ID,
            settings.FEISHU_APP_SECRET,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )
        cli.start()

    thread = threading.Thread(target=_run, daemon=True, name="feishu-ws")
    thread.start()
    logger.info("Feishu WebSocket long-connection client started in background thread")
