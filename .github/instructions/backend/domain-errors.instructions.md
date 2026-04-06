---
applyTo: "backend/app/services/**/errors.py"
---
## Role
- Define all domain-specific exceptions and provide HTTP error mapping in a single file per domain.
- Keep exception definitions and error mapping colocated for discoverability and maintainability.

## File Location
- Each domain package has its own `errors.py`: `app/services/auth/errors.py`, `app/services/content/errors.py`, etc.
- Infrastructure exceptions (`app/services/infrastructure/`) remain in their respective modules (cross-domain, technical nature).

## Exception Definitions

### Naming Convention
- Use `*Error` suffix (not `*Exception`): `FeishuOAuthError`, `ContentNotFoundError`.
- Name should describe the **domain condition**, not the HTTP status.

### Structure
- Inherit from `Exception` directly (no custom base class needed for now).
- Add attributes for contextual data that routers may need for response building:
  ```python
  class ContentNotFoundError(Exception):
      """Raised when content is not found."""

      def __init__(self, content_id: int | None = None, message: str = "content_not_found"):
          super().__init__(message)
          self.content_id = content_id
  ```

### Enum-Based Reason Codes
- For exceptions with multiple failure reasons, use an `Enum` to define reason codes:
  ```python
  class AIServiceErrorReason(str, Enum):
      """Reason codes for AI service errors."""
      TIMEOUT = "ai_timeout"
      PROVIDER_ERROR = "ai_provider_error"
      CONFIG_ERROR = "ai_config_error"

  class AIServiceError(Exception):
      """Raised when AI service encounters an error."""

      def __init__(self, reason: AIServiceErrorReason, message: str | None = None):
          self.reason = reason
          self.message = message or reason.value
          super().__init__(self.message)
  ```
- Benefits: Type-safe reason codes, single exception class for related failures, cleaner mapping logic.

### Grouping
- Group related exceptions with comments:
  ```python
  # ============================================================
  # Auth Errors
  # ============================================================

  class FeishuOAuthError(Exception): ...
  class InvalidTokenError(Exception): ...

  # ============================================================
  # User Errors
  # ============================================================

  class UserNotFoundError(Exception): ...
  ```

## HTTP Error Mapping

### Mapping Function
- Provide a single `raise_<domain>_error(exc: Exception) -> NoReturn` function per domain.
- Function converts domain exceptions to `HTTPException` with standardized `detail` structure.

```python
from typing import NoReturn
from fastapi import HTTPException
from starlette import status


def raise_auth_error(exc: Exception) -> NoReturn:
    """Map auth domain exceptions to HTTP responses."""
    if isinstance(exc, FeishuOAuthError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "feishu_oauth_failed",
                "message": "Feishu OAuth authentication failed.",
            },
        ) from exc

    if isinstance(exc, UserNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "user_not_found",
                "message": "User not found.",
            },
        ) from exc

    # Fallback for unexpected exceptions
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "internal_server_error",
            "message": "An unexpected error occurred.",
        },
    ) from exc
```

### Router Usage
```python
from app.services.auth import FeishuOAuthError, raise_auth_error

@router.get("/callback")
async def feishu_callback(...):
    try:
        session = await login_with_code(db, command=FeishuLoginCommand(code=code))
    except FeishuOAuthError as exc:
        raise_auth_error(exc)
    return TokenOut.from_domain(session)
```

## Infrastructure Exception Handling
- Infrastructure exceptions (e.g., `OSSError`, `httpx.HTTPError`) stay in their modules under `app/services/infrastructure/`.
- **Domain `errors.py` must NOT import infrastructure exceptions directly.**
- Domain services catch infrastructure exceptions internally and convert to domain exceptions:
  ```python
  # In app/services/content/core.py
  from app.services.infrastructure.ai import AIProviderError

  async def analyze_content(...):
      try:
          result = await ai_analyze(...)
      except AIProviderError as exc:
          raise AIServiceError(AIServiceErrorReason.PROVIDER_ERROR) from exc
  ```
- This ensures `errors.py` contains only pure domain exception definitions without infrastructure coupling.

## Export Pattern
- Export exceptions and mapping function from package `__init__.py`:
  ```python
  # app/services/auth/__init__.py
  from .errors import (
      InvalidCredentialsError,
      AccountLockedError,
      raise_auth_error,
  )
  ```

## Cross-Router Shared Helpers
- For exceptions used across multiple domains (e.g., refresh token errors shared by auth and accounts):
  - Define in the owning domain's `errors.py`
  - Import and re-export where needed, or use `app/routers/shared_helpers.py` for mapping functions
