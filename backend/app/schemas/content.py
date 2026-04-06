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
    title: str = Field(..., max_length=256)
    description: str | None = None
    tags: list[str] = []
    content_type: ContentType
    file_key: str

    def to_domain(self, *, uploaded_by: int) -> CreateContentCommand:
        """Convert HTTP request to domain command."""
        return CreateContentCommand(
            title=self.title,
            description=self.description,
            tags=self.tags,
            content_type=self.content_type,
            file_key=self.file_key,
            uploaded_by=uploaded_by,
        )


class ContentUpdateIn(BaseModel):
    title: str | None = Field(None, max_length=256)
    description: str | None = None
    tags: list[str] | None = None

    def to_domain(self) -> UpdateContentCommand:
        """Convert HTTP request to domain command."""
        return UpdateContentCommand(
            title=self.title,
            description=self.description,
            tags=self.tags,
        )


class ContentOut(BaseModel):
    id: int
    title: str
    description: str | None
    tags: list[str]
    content_type: ContentType
    status: ContentStatus
    file_key: str
    file_url: str | None
    file_size: int | None
    ai_summary: str | None
    ai_keywords: list[str]
    uploaded_by: int
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
            ai_summary=output.ai_summary,
            ai_keywords=output.ai_keywords,
            uploaded_by=output.uploaded_by,
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


class ContentListOut(BaseModel):
    total: int
    items: list[ContentOut]


class PresignedUrlOut(BaseModel):
    upload_url: str
    file_key: str

    @classmethod
    def from_domain(cls, output: PresignedUrlOutput) -> PresignedUrlOut:
        """Construct HTTP response from domain output."""
        return cls(upload_url=output.upload_url, file_key=output.file_key)
