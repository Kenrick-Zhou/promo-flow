"""Aliyun OSS storage adapter."""

import logging
import struct
import uuid

import httpx
import oss2
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)

_auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
_bucket = oss2.Bucket(_auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)

_ENV_DIR: dict[str, str] = {
    "development": "dev",
    "production": "prod",
    "test": "test",
}


def _generate_file_key(filename: str, prefix: str = "uploads") -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique = uuid.uuid4().hex
    env_dir = _ENV_DIR[settings.APP_ENV]
    return (
        f"{env_dir}/{prefix}/{unique[:2]}/{unique}.{ext}"
        if ext
        else f"{env_dir}/{prefix}/{unique[:2]}/{unique}"
    )


def _presigned_upload_url(file_key: str, expires: int = 300) -> str:
    return str(_bucket.sign_url("PUT", file_key, expires))


def _presigned_upload_url_with_headers(
    file_key: str,
    expires: int = 300,
    headers: dict[str, str] | None = None,
) -> str:
    return str(_bucket.sign_url("PUT", file_key, expires, headers=headers))


def _presigned_download_url(file_key: str, expires: int = 3600) -> str:
    return str(_bucket.sign_url("GET", file_key, expires))


def _delete_object(file_key: str) -> None:
    _bucket.delete_object(file_key)


def _get_public_url(file_key: str) -> str:
    if settings.OSS_BUCKET_DOMAIN:
        return f"{settings.OSS_BUCKET_DOMAIN.rstrip('/')}/{file_key}"
    return f"{settings.OSS_ENDPOINT.rstrip('/')}/{settings.OSS_BUCKET_NAME}/{file_key}"


# ============================================================
# Async wrappers (sync SDK → threadpool)
# ============================================================


def generate_file_key(filename: str, prefix: str = "uploads") -> str:
    """Generate a unique file key. Pure CPU, no I/O, safe to call directly."""
    return _generate_file_key(filename, prefix)


async def generate_presigned_upload_url(
    file_key: str,
    expires: int = 300,
    headers: dict[str, str] | None = None,
) -> str:
    """Return a presigned PUT URL for direct browser upload."""
    return await run_in_threadpool(
        _presigned_upload_url_with_headers,
        file_key,
        expires,
        headers,
    )


async def generate_presigned_download_url(file_key: str, expires: int = 3600) -> str:
    """Return a presigned GET URL for temporary file access."""
    return await run_in_threadpool(_presigned_download_url, file_key, expires)


async def delete_object(file_key: str) -> None:
    """Delete an object from OSS."""
    await run_in_threadpool(_delete_object, file_key)


def get_public_url(file_key: str) -> str:
    """Return the public URL if bucket is configured for public access. Pure CPU."""
    return _get_public_url(file_key)


def _parse_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    """Extract width/height from JPEG binary data by scanning SOF markers."""
    i = 0
    length = len(data)
    if length < 2 or data[0:2] != b"\xff\xd8":
        return None
    i = 2
    while i < length - 1:
        if data[i] != 0xFF:
            break
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            if i + 9 < length:
                height = struct.unpack(">H", data[i + 5 : i + 7])[0]
                width = struct.unpack(">H", data[i + 7 : i + 9])[0]
                return (width, height)
            return None
        if marker == 0xD9:
            break
        if i + 3 < length:
            seg_len = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + seg_len
        else:
            break
    return None


async def get_media_dimensions(
    file_url: str, content_type: str
) -> tuple[int, int] | None:
    """Fetch original media dimensions (width, height) from OSS.

    - Image: uses OSS image/info processing API.
    - Video: fetches first-frame snapshot and parses JPEG dimensions.
    Returns None on any failure (non-critical).
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if content_type == "image":
                resp = await client.get(f"{file_url}?x-oss-process=image/info")
                resp.raise_for_status()
                info = resp.json()
                width = int(info["ImageWidth"]["value"])
                height = int(info["ImageHeight"]["value"])
                return (width, height)

            if content_type == "video":
                snapshot_url = (
                    f"{file_url}?x-oss-process="
                    "video/snapshot,t_0,f_jpg,w_0,h_0,m_fast"
                )
                resp = await client.get(snapshot_url)
                resp.raise_for_status()
                dims = _parse_jpeg_dimensions(resp.content)
                return dims

    except Exception:
        logger.warning(
            "Failed to get media dimensions for content_type=%s",
            content_type,
            exc_info=True,
        )
    return None
