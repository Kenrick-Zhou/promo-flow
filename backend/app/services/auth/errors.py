"""Auth service domain errors."""

from typing import NoReturn

from fastapi import HTTPException
from starlette import status

# ============================================================
# Exceptions
# ============================================================


class FeishuOAuthError(Exception):
    """Raised when Feishu OAuth flow fails."""

    def __init__(self, message: str = "feishu_oauth_failed"):
        super().__init__(message)


class InvalidTokenError(Exception):
    """Raised when JWT token is invalid or expired."""

    def __init__(self, message: str = "invalid_token"):
        super().__init__(message)


class UserNotFoundError(Exception):
    """Raised when user is not found."""

    def __init__(self, message: str = "user_not_found"):
        super().__init__(message)


class InsufficientPermissionError(Exception):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "insufficient_permission"):
        super().__init__(message)


# ============================================================
# HTTP Error Mapping
# ============================================================


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

    if isinstance(exc, InvalidTokenError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "invalid_token",
                "message": "Invalid or expired token.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if isinstance(exc, UserNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "user_not_found",
                "message": "User not found.",
            },
        ) from exc

    if isinstance(exc, InsufficientPermissionError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "insufficient_permission",
                "message": "Insufficient permissions.",
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "auth_internal_error",
            "message": "An unexpected authentication error occurred.",
        },
    ) from exc
