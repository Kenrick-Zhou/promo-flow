"""Content domain types."""

from __future__ import annotations

import enum
from dataclasses import dataclass

# ============================================================
# Enumerations
# ============================================================


class ContentStatus(str, enum.Enum):
    """Content review status."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ContentType(str, enum.Enum):
    """Supported media types."""

    image = "image"
    video = "video"
    document = "document"


class UserRole(str, enum.Enum):
    """System user roles."""

    employee = "employee"
    reviewer = "reviewer"
    admin = "admin"


class AiStatus(str, enum.Enum):
    """AI processing status for content."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AuditDecision(str, enum.Enum):
    """Audit review decisions."""

    approved = "approved"
    rejected = "rejected"


# ============================================================
# Command Objects
# ============================================================


@dataclass(slots=True)
class CreateContentCommand:
    """Command for creating new content."""

    title: str | None
    description: str | None
    tag_names: list[str]
    content_type: ContentType
    file_key: str
    uploaded_by: int
    category_id: int


@dataclass(slots=True)
class UpdateContentCommand:
    """Command for updating existing content."""

    title: str | None = None
    description: str | None = None
    tag_names: list[str] | None = None
    category_id: int | None = None


@dataclass(slots=True)
class AuditContentCommand:
    """Command for auditing content."""

    content_id: int
    auditor_id: int
    decision: AuditDecision
    comments: str | None = None


@dataclass(slots=True)
class SearchContentCommand:
    """Command for semantic content search."""

    query: str
    limit: int = 10
    content_type: str | None = None


@dataclass(slots=True)
class EditContentMetadataCommand:
    """Command for reviewer editing title/summary."""

    content_id: int
    title: str | None = None
    ai_summary: str | None = None


# ============================================================
# Output Objects
# ============================================================


@dataclass(slots=True)
class ContentOutput:
    """Content data returned by service layer."""

    id: int
    title: str | None
    description: str | None
    tags: list[str]
    content_type: ContentType
    status: ContentStatus
    file_key: str
    file_url: str | None
    file_size: int | None
    ai_summary: str | None
    ai_keywords: list[str]
    ai_status: AiStatus
    ai_error: str | None
    ai_processed_at: str | None
    uploaded_by: int
    category_id: int | None
    category_name: str | None
    primary_category_name: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ContentListOutput:
    """Paginated content list returned by service layer."""

    total: int
    items: list[ContentOutput]


@dataclass(slots=True)
class AuditLogOutput:
    """Audit log entry returned by service layer."""

    id: int
    content_id: int
    auditor_id: int
    audit_status: str
    audit_comments: str | None
    audit_time: str


@dataclass(slots=True)
class SearchResultOutput:
    """Single search result with relevance score."""

    content: ContentOutput
    score: float


@dataclass(slots=True)
class PresignedUrlOutput:
    """Presigned upload URL result."""

    upload_url: str
    file_key: str
    upload_headers: dict[str, str]
