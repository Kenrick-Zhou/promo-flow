"""Search service package."""

from app.services.search.core import semantic_search
from app.services.search.core_unified import search_contents
from app.services.search.errors import (
    EmbeddingGenerationError,
    SearchError,
    raise_search_error,
)

__all__ = [
    "search_contents",
    "semantic_search",
    "EmbeddingGenerationError",
    "SearchError",
    "raise_search_error",
]
