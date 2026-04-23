"""Search router error mapping helpers."""

from typing import NoReturn

from fastapi import HTTPException
from starlette import status


def raise_search_error(exc: Exception) -> NoReturn:
    """Convert unexpected search failures into the unified HTTP error contract."""
    if isinstance(exc, HTTPException):
        raise exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "error_code": "search_internal_error",
            "message": "An unexpected search error occurred.",
        },
    ) from exc
