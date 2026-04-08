"""Content service domain errors."""

from typing import NoReturn

from fastapi import HTTPException
from starlette import status

# ============================================================
# Exceptions
# ============================================================


class ContentNotFoundError(Exception):
    """Raised when content is not found."""

    def __init__(
        self, content_id: int | None = None, message: str = "content_not_found"
    ):
        super().__init__(message)
        self.content_id = content_id


class ContentForbiddenError(Exception):
    """Raised when user lacks permission for a content operation."""

    def __init__(self, message: str = "content_forbidden"):
        super().__init__(message)


class InvalidAuditActionError(Exception):
    """Raised when audit action is invalid."""

    def __init__(self, message: str = "invalid_audit_action"):
        super().__init__(message)


class InvalidCategoryError(Exception):
    """Raised when content is assigned to an invalid category."""

    def __init__(self, message: str = "invalid_category"):
        super().__init__(message)


# ============================================================
# HTTP Error Mapping
# ============================================================


def raise_content_error(exc: Exception) -> NoReturn:
    """Map content domain exceptions to HTTP responses."""
    if isinstance(exc, ContentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "content_not_found",
                "message": "Content not found.",
            },
        ) from exc

    if isinstance(exc, ContentForbiddenError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "content_forbidden",
                "message": "You don't have permission for this content operation.",
            },
        ) from exc

    if isinstance(exc, InvalidAuditActionError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "invalid_audit_action",
                "message": "Audit status must be 'approved' or 'rejected'.",
            },
        ) from exc

    if isinstance(exc, InvalidCategoryError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "invalid_category",
                "message": str(exc),
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "content_internal_error",
            "message": "An unexpected content error occurred.",
        },
    ) from exc
