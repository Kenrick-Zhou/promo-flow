"""Request ID middleware and unified error handling."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID into every request/response."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for unified error responses."""

    @app.exception_handler(422)
    async def validation_exception_handler(request: Request, exc):
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "validation_error",
                "message": "Validation failed",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
