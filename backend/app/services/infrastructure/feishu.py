"""Feishu (Lark) SDK client adapter."""

from __future__ import annotations

import io
import json
import logging
from functools import lru_cache
from types import SimpleNamespace
from typing import IO, TYPE_CHECKING, Any

from app.core.config import settings

if TYPE_CHECKING:
    import lark_oapi as lark

logger = logging.getLogger("promoflow.api")

# ---------------------------------------------------------------------------
# Singleton client – token lifecycle managed automatically by SDK
# ---------------------------------------------------------------------------

_client: Any | None = None


@lru_cache(maxsize=1)
def _get_lark_sdk() -> SimpleNamespace:
    """Lazily import Feishu SDK to avoid import-time side effects in tests."""
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateFileRequest,
        CreateFileRequestBody,
        CreateImageRequest,
        CreateImageRequestBody,
        CreateMessageRequest,
        CreateMessageRequestBody,
    )

    return SimpleNamespace(
        lark=lark,
        CreateFileRequest=CreateFileRequest,
        CreateFileRequestBody=CreateFileRequestBody,
        CreateImageRequest=CreateImageRequest,
        CreateImageRequestBody=CreateImageRequestBody,
        CreateMessageRequest=CreateMessageRequest,
        CreateMessageRequestBody=CreateMessageRequestBody,
    )


def get_lark_client() -> lark.Client:
    sdk = _get_lark_sdk()
    global _client
    if _client is None:
        _client = (
            sdk.lark.Client.builder()
            .app_id(settings.FEISHU_APP_ID)
            .app_secret(settings.FEISHU_APP_SECRET)
            .log_level(sdk.lark.LogLevel.INFO)
            .build()
        )
    return _client


# ---------------------------------------------------------------------------
# Messaging helpers
# ---------------------------------------------------------------------------


async def send_text_to_chat(chat_id: str, text: str) -> None:
    """Send a plain text message to a group chat."""
    sdk = _get_lark_sdk()
    client = get_lark_client()
    req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}))
            .build()
        )
        .build()
    )
    resp = await client.im.v1.message.acreate(req)
    if not resp.success():
        logger.error("send_text_to_chat failed: code=%s msg=%s", resp.code, resp.msg)


async def send_markdown_to_user(open_id: str, title: str, markdown: str) -> None:
    """Send a markdown-based interactive card to a user by open_id."""
    sdk = _get_lark_sdk()
    client = get_lark_client()
    card = {
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": title},
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": markdown,
                },
            }
        ],
    }
    req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("interactive")
            .content(json.dumps(card, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = await client.im.v1.message.acreate(req)
    if not resp.success():
        logger.error(
            "Feishu send markdown to user failed: code=%s msg=%s",
            resp.code,
            resp.msg,
        )
        raise RuntimeError(f"failed to send markdown message: {resp.code} {resp.msg}")
    logger.info("Feishu markdown message sent to open_id=%s", open_id)


async def send_image_to_user(open_id: str, file_bytes: bytes, file_name: str) -> None:
    """Upload image to Feishu then send to user by open_id."""
    sdk = _get_lark_sdk()
    client = get_lark_client()

    # 1. Upload image
    upload_req = (
        sdk.CreateImageRequest.builder()
        .request_body(
            sdk.CreateImageRequestBody.builder()
            .image_type("message")
            .image(io.BytesIO(file_bytes))
            .build()
        )
        .build()
    )
    upload_resp = await client.im.v1.image.acreate(upload_req)
    if not upload_resp.success():
        logger.error(
            "Feishu image upload failed: code=%s msg=%s",
            upload_resp.code,
            upload_resp.msg,
        )
        return

    image_key = upload_resp.data.image_key
    logger.info("Feishu image uploaded: image_key=%s", image_key)

    # 2. Send to user
    send_req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("image")
            .content(json.dumps({"image_key": image_key}))
            .build()
        )
        .build()
    )
    send_resp = await client.im.v1.message.acreate(send_req)
    if not send_resp.success():
        logger.error(
            "Feishu send image to user failed: code=%s msg=%s",
            send_resp.code,
            send_resp.msg,
        )
    else:
        logger.info("Feishu image sent to open_id=%s", open_id)


async def send_file_to_user(open_id: str, file_bytes: bytes, file_name: str) -> None:
    """Upload file (video) to Feishu then send to user by open_id."""
    sdk = _get_lark_sdk()
    client = get_lark_client()

    # 1. Upload file – use "stream" so it can be sent as msg_type="file"
    #    (file_type="mp4" creates a "media" resource that requires an image cover)
    upload_req = (
        sdk.CreateFileRequest.builder()
        .request_body(
            sdk.CreateFileRequestBody.builder()
            .file_type("stream")
            .file_name(file_name)
            .file(io.BytesIO(file_bytes))
            .build()
        )
        .build()
    )
    upload_resp = await client.im.v1.file.acreate(upload_req)
    if not upload_resp.success():
        logger.error(
            "Feishu file upload failed: code=%s msg=%s",
            upload_resp.code,
            upload_resp.msg,
        )
        return

    file_key = upload_resp.data.file_key
    logger.info("Feishu file uploaded: file_key=%s", file_key)

    # 2. Send to user
    send_req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("file")
            .content(json.dumps({"file_key": file_key}))
            .build()
        )
        .build()
    )
    send_resp = await client.im.v1.message.acreate(send_req)
    if not send_resp.success():
        logger.error(
            "Feishu send file to user failed: code=%s msg=%s",
            send_resp.code,
            send_resp.msg,
        )
    else:
        logger.info("Feishu file sent to open_id=%s", open_id)


# ---------------------------------------------------------------------------
# Synchronous helpers – for use inside asyncio.to_thread / thread pools,
# where streaming IO objects backed by live network connections can be read
# without crossing the async boundary.
# ---------------------------------------------------------------------------


def send_image_to_user_sync(
    open_id: str, file_stream: IO[bytes], file_name: str
) -> None:
    """Upload image stream to Feishu then DM the user (synchronous)."""
    sdk = _get_lark_sdk()
    client = get_lark_client()

    upload_req = (
        sdk.CreateImageRequest.builder()
        .request_body(
            sdk.CreateImageRequestBody.builder()
            .image_type("message")
            .image(file_stream)
            .build()
        )
        .build()
    )
    upload_resp = client.im.v1.image.create(upload_req)
    if not upload_resp.success():
        logger.error(
            "Feishu image upload failed (sync): code=%s msg=%s",
            upload_resp.code,
            upload_resp.msg,
        )
        return

    image_key = upload_resp.data.image_key
    logger.info("Feishu image uploaded (sync): image_key=%s", image_key)

    send_req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("image")
            .content(json.dumps({"image_key": image_key}))
            .build()
        )
        .build()
    )
    send_resp = client.im.v1.message.create(send_req)
    if not send_resp.success():
        logger.error(
            "Feishu send image to user failed (sync): code=%s msg=%s",
            send_resp.code,
            send_resp.msg,
        )
    else:
        logger.info("Feishu image sent (sync): open_id=%s", open_id)


def send_file_to_user_sync(
    open_id: str, file_stream: IO[bytes], file_name: str
) -> None:
    """Upload file stream to Feishu then DM the user (synchronous)."""
    sdk = _get_lark_sdk()
    client = get_lark_client()

    upload_req = (
        sdk.CreateFileRequest.builder()
        .request_body(
            sdk.CreateFileRequestBody.builder()
            .file_type("stream")
            .file_name(file_name)
            .file(file_stream)
            .build()
        )
        .build()
    )
    upload_resp = client.im.v1.file.create(upload_req)
    if not upload_resp.success():
        logger.error(
            "Feishu file upload failed (sync): code=%s msg=%s",
            upload_resp.code,
            upload_resp.msg,
        )
        return

    file_key = upload_resp.data.file_key
    logger.info("Feishu file uploaded (sync): file_key=%s", file_key)

    send_req = (
        sdk.CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            sdk.CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("file")
            .content(json.dumps({"file_key": file_key}))
            .build()
        )
        .build()
    )
    send_resp = client.im.v1.message.create(send_req)
    if not send_resp.success():
        logger.error(
            "Feishu send file to user failed (sync): code=%s msg=%s",
            send_resp.code,
            send_resp.msg,
        )
    else:
        logger.info("Feishu file sent (sync): open_id=%s", open_id)
