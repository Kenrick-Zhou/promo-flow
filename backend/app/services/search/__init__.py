"""Search service package."""

from app.services.search.core import search_contents
from app.services.search.errors import raise_search_error

__all__ = [
    "search_contents",
    "raise_search_error",
]
