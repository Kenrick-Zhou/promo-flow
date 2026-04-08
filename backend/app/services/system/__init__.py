"""System management service package (categories and tags)."""

from app.services.system.core import (
    create_category,
    create_tag,
    delete_category,
    delete_tag,
    get_category,
    get_tag,
    list_categories_tree,
    list_tags,
    reorder_tags,
    update_category,
    update_tag,
)
from app.services.system.errors import (
    CategoryHasChildrenError,
    CategoryHasContentsError,
    CategoryNotFoundError,
    DuplicateCategoryError,
    DuplicateTagError,
    TagInUseError,
    TagNotFoundError,
    raise_system_error,
)

__all__ = [
    "create_category",
    "create_tag",
    "delete_category",
    "delete_tag",
    "get_category",
    "get_tag",
    "list_categories_tree",
    "list_tags",
    "reorder_tags",
    "update_category",
    "update_tag",
    "CategoryHasChildrenError",
    "CategoryHasContentsError",
    "CategoryNotFoundError",
    "DuplicateCategoryError",
    "DuplicateTagError",
    "TagInUseError",
    "TagNotFoundError",
    "raise_system_error",
]
