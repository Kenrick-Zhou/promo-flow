from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.content import (
    ContentOutput,
    ContentStatus,
    ContentType,
    CreateContentCommand,
    PresignedUrlOutput,
    UpdateContentCommand,
)


class ContentCreateIn(BaseModel):
    title: str | None = Field(None, max_length=256)
    description: str | None = None
    tag_names: list[str] = []
    content_type: ContentType
    file_key: str
    category_id: int

    def to_domain(self, *, uploaded_by: int) -> CreateContentCommand:
        """Convert HTTP request to domain command."""
        return CreateContentCommand(
            title=self.title,
            description=self.description,
            tag_names=self.tag_names,
            content_type=self.content_type,
            file_key=self.file_key,
            uploaded_by=uploaded_by,
            category_id=self.category_id,
        )


class ContentUpdateIn(BaseModel):
    title: str | None = Field(None, max_length=256)
    description: str | None = None
    tag_names: list[str] | None = None
    category_id: int | None = None

    def to_domain(self) -> UpdateContentCommand:
        """Convert HTTP request to domain command."""
        return UpdateContentCommand(
            title=self.title,
            description=self.description,
            tag_names=self.tag_names,
            category_id=self.category_id,
        )


class ContentOut(BaseModel):
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
    ai_status: str
    ai_error: str | None
    ai_processed_at: str | None
    uploaded_by: int
    uploaded_by_name: str
    category_id: int | None
    category_name: str | None
    primary_category_name: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, output: ContentOutput) -> ContentOut:
        """Construct HTTP response from domain output."""
        return cls(
            id=output.id,
            title=output.title,
            description=output.description,
            tags=output.tags,
            content_type=output.content_type,
            status=output.status,
            file_key=output.file_key,
            file_url=output.file_url,
            file_size=output.file_size,
            media_width=output.media_width,
            media_height=output.media_height,
            view_count=output.view_count,
            download_count=output.download_count,
            ai_summary=output.ai_summary,
            ai_keywords=output.ai_keywords,
            ai_status=output.ai_status.value,
            ai_error=output.ai_error,
            ai_processed_at=output.ai_processed_at,
            uploaded_by=output.uploaded_by,
            uploaded_by_name=output.uploaded_by_name,
            category_id=output.category_id,
            category_name=output.category_name,
            primary_category_name=output.primary_category_name,
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


class ContentListOut(BaseModel):
    total: int
    items: list[ContentOut]


class PresignedUrlOut(BaseModel):
    upload_url: str
    file_key: str
    upload_headers: dict[str, str]

    @classmethod
    def from_domain(cls, output: PresignedUrlOutput) -> PresignedUrlOut:
        """Construct HTTP response from domain output."""
        return cls(
            upload_url=output.upload_url,
            file_key=output.file_key,
            upload_headers=output.upload_headers,
        )
