---
applyTo: "backend/app/routers/*.py, backend/app/schemas/*.py, backend/tests/**"
---
## Unified Response Structure
- Success: return response models defined in `schemas`; avoid constructing dicts in routes.
- Failure: raise `HTTPException` with `detail` shaped as `{ "error_code": string, "message": string }`.
  - The custom `HTTPException` handler in `app/core/middleware.py` flattens the `detail` dict to the **top level** of the response body and injects `request_id`. This is NOT automatic from FastAPI/Starlette — the handler is required.
  - The `RequestIdMiddleware` injects `X-Request-ID` into response headers.

> **Important**: The error body format `{"error_code": ..., "message": ..., "request_id": ...}` at the top level only works because `register_exception_handlers()` in `middleware.py` registers a custom `StarletteHTTPException` handler. Without it, FastAPI wraps `detail` under `{"detail": {...}}`. Do not remove this handler.

## Suggested Error Classes
- `400` Parameter/business validation failure
- `401` Unauthenticated or invalid token
- `403` Forbidden (insufficient role/permission)
- `404` Resource not found
- `409` Concurrency/uniqueness conflict
- `422` Semantic validation failure (Pydantic)
- `5xx` Dependency failure or unknown error

## Docs and Examples
- In route `responses`, provide example structures for common errors to aid client integration.

Example error body and header:

```json
{
  "error_code": "content_not_found",
  "message": "Content not found.",
  "request_id": "a1b2c3d4e5"
}
```

Header:

```
X-Request-ID: a1b2c3d4e5
```

- Logging levels: map `4xx` as warnings; map `5xx` and unexpected errors as exceptions (with stack traces).
- Testing: API contract changes require tests to verify error responses and success cases match documented examples.
