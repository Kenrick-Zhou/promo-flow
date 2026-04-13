"""Content service package."""

from app.services.content.core import (
    audit_content,
    create_content,
    delete_content,
    edit_content_metadata,
    get_content,
    get_content_orm,
    increment_download_count,
    increment_view_count,
    list_contents,
    mark_content_ai_failed,
    mark_content_ai_processing,
    send_file_to_user,
    update_content,
    update_content_ai_fields,
    update_content_media_dimensions,
)
from app.services.content.errors import (
    ContentForbiddenError,
    ContentNotFoundError,
    InvalidAuditActionError,
    InvalidCategoryError,
    raise_content_error,
)

__all__ = [
    "audit_content",
    "create_content",
    "delete_content",
    "edit_content_metadata",
    "get_content",
    "get_content_orm",
    "increment_download_count",
    "increment_view_count",
    "list_contents",
    "mark_content_ai_failed",
    "mark_content_ai_processing",
    "send_file_to_user",
    "update_content",
    "update_content_ai_fields",
    "update_content_media_dimensions",
    "ContentForbiddenError",
    "ContentNotFoundError",
    "InvalidAuditActionError",
    "InvalidCategoryError",
    "raise_content_error",
]
