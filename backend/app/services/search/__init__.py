"""Search service package."""

from app.services.search.core import semantic_search
from app.services.search.errors import (
    EmbeddingGenerationError,
    SearchError,
    raise_search_error,
)

__all__ = [
    "semantic_search",
    "EmbeddingGenerationError",
    "SearchError",
    "raise_search_error",
]
