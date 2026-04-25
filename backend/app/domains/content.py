"""Content domain types."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

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
class BatchCreateContentItem:
    """A single file entry within a batch create command."""

    content_type: ContentType
    file_key: str


@dataclass(slots=True)
class BatchCreateContentCommand:
    """Command for creating multiple contents that share metadata."""

    items: list[BatchCreateContentItem]
    description: str | None
    tag_names: list[str]
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
    """Command for content search."""

    query: str
    limit: int = 10
    content_type: str | None = None
    enable_rerank: bool | None = None
    allow_query_limit_override: bool = False


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
    media_width: int | None
    media_height: int | None
    view_count: int
    download_count: int
    ai_summary: str | None
    ai_keywords: list[str]
    ai_status: AiStatus
    ai_error: str | None
    ai_processed_at: str | None
    uploaded_by: int
    uploaded_by_name: str
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
    """Single search result with relevance scores."""

    content: ContentOutput
    final_score: float
    lexical_score: float
    semantic_score: float
    matched_signals: list[str]
    reranked: bool


@dataclass(slots=True)
class ParsedQuery:
    """Output of query understanding stage."""

    raw_query: str
    normalized_query: str
    parsed_content_type: str | None
    must_terms: list[str]
    should_terms: list[str]
    query_embedding_text: str
    need_llm_rerank: bool
    llm_used: bool
    sort_intent: str | None = None
    time_intent: dict[str, str | int] | None = None
    exclude_terms: list[str] = field(default_factory=list)
    limit_intent: int | None = None


@dataclass(slots=True)
class SearchTimingOutput:
    """Per-stage timing for a search request."""

    query_parse_ms: float
    vector_recall_ms: float
    fts_recall_ms: float
    tag_recall_ms: float
    rrf_merge_ms: float
    scoring_ms: float
    llm_rerank_ms: float | None
    total_ms: float


@dataclass(slots=True)
class SearchOutput:
    """Unified search result returned by search_contents()."""

    results: list[SearchResultOutput]
    timing: SearchTimingOutput | None
    query_info: ParsedQuery


@dataclass(slots=True)
class PresignedUrlOutput:
    """Presigned upload URL result."""

    upload_url: str
    file_key: str
    upload_headers: dict[str, str]
