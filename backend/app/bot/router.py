"""Feishu bot webhook router."""

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request

from app.bot.handlers import handle_message_event
from app.core.config import settings

router = APIRouter(prefix="/bot", tags=["bot"])


def _verify_signature(timestamp: str, nonce: str, body: str, expected: str) -> bool:
    """Verify Feishu webhook signature."""
    key = settings.FEISHU_ENCRYPT_KEY.encode()
    content = f"{timestamp}{nonce}{body}".encode()
    sig = hmac.new(key, content, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


@router.post("/webhook")
async def feishu_webhook(request: Request):
    """Receive Feishu bot events (challenge + message events)."""
    data = await request.json()

    # URL verification challenge
    if data.get("type") == "url_verification":
        if data.get("token") != settings.FEISHU_VERIFICATION_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid token")
        return {"challenge": data["challenge"]}

    # Process message events
    header = data.get("header", {})
    if header.get("event_type") == "im.message.receive_v1":
        await handle_message_event(data.get("event", {}))

    return {"code": 0}
