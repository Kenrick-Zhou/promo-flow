"""Request ID middleware and unified error handling."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("promoflow.api")


def _log_json(
    *,
    level: int,
    message: str,
    request: Request,
    status_code: int,
    duration_ms: float | None = None,
    error_code: str | None = None,
    exc_info: BaseException | None = None,
) -> None:
    payload: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "message": message,
        "request_id": getattr(request.state, "request_id", "unknown"),
        "status_code": status_code,
        "method": request.method,
        "path": request.url.path,
    }
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if error_code:
        payload["error_code"] = error_code
    if exc_info is not None:
        payload["exc_info"] = exc_info.__class__.__name__

    logger.log(level, json.dumps(payload, ensure_ascii=False), exc_info=exc_info)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into every request/response."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        request.state.request_id = request_id
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        error_code = getattr(request.state, "error_code", None)
        if response.status_code >= 500:
            _log_json(
                level=logging.ERROR,
                message="request_failed",
                request=request,
                status_code=response.status_code,
                duration_ms=duration_ms,
                error_code=error_code,
            )
        elif response.status_code >= 400:
            _log_json(
                level=logging.WARNING,
                message="request_failed",
                request=request,
                status_code=response.status_code,
                duration_ms=duration_ms,
                error_code=error_code,
            )
        response.headers["X-Request-ID"] = request_id
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for unified error responses."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", "unknown")
        detail = exc.detail
        if isinstance(detail, dict) and "error_code" in detail:
            request.state.error_code = detail["error_code"]
            content = {**detail, "request_id": request_id}
        else:
            request.state.error_code = "http_error"
            content = {
                "error_code": "http_error",
                "message": str(detail) if detail else exc.__class__.__name__,
                "request_id": request_id,
            }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        request.state.error_code = "validation_error"
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "validation_error",
                "message": "Validation failed",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        request.state.error_code = "internal_server_error"
        _log_json(
            level=logging.ERROR,
            message="unhandled_exception",
            request=request,
            status_code=500,
            error_code="internal_server_error",
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "internal_server_error",
                "message": "Internal server error.",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
