"""Aliyun OSS storage adapter."""

import uuid

import oss2
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

_auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
_bucket = oss2.Bucket(_auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET_NAME)


def _generate_file_key(filename: str, prefix: str = "uploads") -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique = uuid.uuid4().hex
    return (
        f"{prefix}/{unique[:2]}/{unique}.{ext}"
        if ext
        else f"{prefix}/{unique[:2]}/{unique}"
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
