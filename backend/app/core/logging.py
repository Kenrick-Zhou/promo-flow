"""Application logging configuration helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

_APP_LOGGER_NAMES = ("app", "promoflow.api")
_HANDLER_NAME = "promoflow.console"
_REDACTED = "[redacted]"

_MASKED_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], bool], ...] = (
    (
        re.compile(
            r"(?P<prefix>\b(?:open_id|chat_id|image_key|file_key)=)(?P<value>[^\s|,;]+)",
            re.IGNORECASE,
        ),
        True,
    ),
    (
        re.compile(
            r"(?P<prefix>\b(?:client_id|redirect_uri|url)=)(?P<value>[^\s|,;]+)",
            re.IGNORECASE,
        ),
        False,
    ),
)
_MASKED_PAYLOAD_FIELDS = frozenset({"open_id", "chat_id", "image_key", "file_key"})
_REDACTED_PAYLOAD_FIELDS = frozenset(
    {
        "authorization_url",
        "client_id",
        "file_url",
        "query",
        "query_preview",
        "query_text",
        "redirect_uri",
        "secret",
        "text",
        "token",
        "url",
    }
)


def mask_identifier(value: str | None) -> str | None:
    """Mask identifiers while preserving a tiny bit of shape for correlation."""
    if value is None:
        return None
    if len(value) <= 6:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def fingerprint_text(value: str | None) -> str | None:
    """Return a short stable fingerprint for sensitive free-form text."""
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _sanitize_message_text(message: str) -> str:
    sanitized = message

    for pattern, should_mask in _MASKED_TEXT_PATTERNS:

        def _replace(match: re.Match[str], *, _should_mask: bool = should_mask) -> str:
            prefix = match.group("prefix")
            value = match.group("value")
            replacement = mask_identifier(value) if _should_mask else _REDACTED
            return f"{prefix}{replacement}"

        sanitized = pattern.sub(_replace, sanitized)

    return sanitized


def _sanitize_payload(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            nested_key: _sanitize_payload(nested_value, key=nested_key)
            for nested_key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        if key in _MASKED_PAYLOAD_FIELDS:
            return mask_identifier(value)
        if key in _REDACTED_PAYLOAD_FIELDS:
            return _REDACTED
        return _sanitize_message_text(value)
    return value


def _decode_json_message(message: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class _JsonFormatter(logging.Formatter):
    """Render all application logs as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        rendered_message = record.getMessage()
        payload = _decode_json_message(rendered_message)
        if payload is None:
            payload = {"message": _sanitize_message_text(rendered_message)}
        else:
            payload = _sanitize_payload(payload)

        payload.setdefault("timestamp", datetime.now(UTC).isoformat())
        payload.setdefault("level", record.levelname)
        payload.setdefault("logger", record.name)

        if record.exc_info is not None:
            exc_type = record.exc_info[0]
            if exc_type is not None:
                payload.setdefault("exc_info", exc_type.__name__)
            payload.setdefault("stack_trace", self.formatException(record.exc_info))

        return json.dumps(payload, ensure_ascii=False)


def _build_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.set_name(_HANDLER_NAME)
    handler.setLevel(logging.INFO)
    handler.setFormatter(_JsonFormatter())
    return handler


def _ensure_logger_handler(logger: logging.Logger) -> None:
    if any(handler.get_name() == _HANDLER_NAME for handler in logger.handlers):
        return
    logger.addHandler(_build_handler())


def configure_logging() -> None:
    """Attach INFO handlers for application loggers without touching third parties."""
    for logger_name in _APP_LOGGER_NAMES:
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = False
        _ensure_logger_handler(app_logger)
