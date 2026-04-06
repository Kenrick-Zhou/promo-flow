"""Search service domain errors."""

from typing import NoReturn

from fastapi import HTTPException
from starlette import status

# ============================================================
# Exceptions
# ============================================================


class SearchError(Exception):
    """Raised when search operation fails."""

    def __init__(self, message: str = "search_failed"):
        super().__init__(message)


class EmbeddingGenerationError(Exception):
    """Raised when embedding generation fails."""

    def __init__(self, message: str = "embedding_generation_failed"):
        super().__init__(message)


# ============================================================
# HTTP Error Mapping
# ============================================================


def raise_search_error(exc: Exception) -> NoReturn:
    """Map search domain exceptions to HTTP responses."""
    if isinstance(exc, EmbeddingGenerationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "embedding_generation_failed",
                "message": "Failed to generate embedding for search query.",
            },
        ) from exc

    if isinstance(exc, SearchError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "search_failed",
                "message": "Search operation failed.",
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "search_internal_error",
            "message": "An unexpected search error occurred.",
        },
    ) from exc
