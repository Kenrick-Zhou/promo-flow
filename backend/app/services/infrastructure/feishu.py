"""Feishu (Lark) SDK client adapter."""

from __future__ import annotations

import io
import json
import logging
from typing import IO

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateFileRequest,
    CreateFileRequestBody,
    CreateImageRequest,
    CreateImageRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
)

from app.core.config import settings

logger = logging.getLogger("promoflow.api")

# ---------------------------------------------------------------------------
# Singleton client – token lifecycle managed automatically by SDK
# ---------------------------------------------------------------------------

_client: lark.Client | None = None


def get_lark_client() -> lark.Client:
    global _client
    if _client is None:
        _client = (
            lark.Client.builder()
            .app_id(settings.FEISHU_APP_ID)
            .app_secret(settings.FEISHU_APP_SECRET)
            .log_level(lark.LogLevel.INFO)
            .build()
        )
    return _client


# ---------------------------------------------------------------------------
# Messaging helpers
# ---------------------------------------------------------------------------


async def send_text_to_chat(chat_id: str, text: str) -> None:
    """Send a plain text message to a group chat."""
    client = get_lark_client()
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
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


async def send_image_to_user(open_id: str, file_bytes: bytes, file_name: str) -> None:
    """Upload image to Feishu then send to user by open_id."""
    client = get_lark_client()

    # 1. Upload image
    upload_req = (
        CreateImageRequest.builder()
        .request_body(
            CreateImageRequestBody.builder()
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
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
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
    client = get_lark_client()

    # 1. Upload file – use "stream" so it can be sent as msg_type="file"
    #    (file_type="mp4" creates a "media" resource that requires an image cover)
    upload_req = (
        CreateFileRequest.builder()
        .request_body(
            CreateFileRequestBody.builder()
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
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
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
    client = get_lark_client()

    upload_req = (
        CreateImageRequest.builder()
        .request_body(
            CreateImageRequestBody.builder()
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
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
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
    client = get_lark_client()

    upload_req = (
        CreateFileRequest.builder()
        .request_body(
            CreateFileRequestBody.builder()
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
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
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
