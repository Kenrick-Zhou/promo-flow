"""Feishu bot webhook router."""

import hashlib
import hmac

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.bot.handlers import (
    handle_message_event,
    register_group_chat,
    unregister_group_chat,
)
from app.core.config import settings

router = APIRouter(prefix="/bot", tags=["bot"])


def _verify_signature(timestamp: str, nonce: str, body: str, expected: str) -> bool:
    """Verify Feishu webhook signature."""
    key = settings.FEISHU_ENCRYPT_KEY.encode()
    content = f"{timestamp}{nonce}{body}".encode()
    sig = hmac.new(key, content, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@router.post("/webhook")
async def feishu_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Feishu bot events (challenge + message + group membership events)."""
    data = await request.json()

    # URL verification challenge
    if data.get("type") == "url_verification":
        if data.get("token") != settings.FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")
        return {"challenge": data["challenge"]}

    header = data.get("header", {})
    event_type = header.get("event_type", "")
    event = data.get("event", {})

    # Bot added to a group chat
    if event_type == "im.chat.member.bot.added_v1":
        chat_id = event.get("chat_id", "")
        chat_name = event.get("name", None)
        if chat_id:
            background_tasks.add_task(register_group_chat, chat_id, chat_name)

    # Bot removed from a group chat
    elif event_type == "im.chat.member.bot.deleted_v1":
        chat_id = event.get("chat_id", "")
        if chat_id:
            background_tasks.add_task(unregister_group_chat, chat_id)

    # Process message events
    elif event_type == "im.message.receive_v1":
        await handle_message_event(event)

    return {"code": 0}
