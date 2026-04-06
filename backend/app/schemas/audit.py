from __future__ import annotations

from pydantic import BaseModel

from app.domains.content import (
    AuditContentCommand,
    AuditDecision,
    AuditLogOutput,
    SearchContentCommand,
    SearchResultOutput,
)
from app.schemas.content import ContentOut


class AuditActionIn(BaseModel):
    status: AuditDecision
    comments: str | None = None

    def to_domain(self, *, content_id: int, auditor_id: int) -> AuditContentCommand:
        """Convert HTTP request to domain command."""
        return AuditContentCommand(
            content_id=content_id,
            auditor_id=auditor_id,
            decision=self.status,
            comments=self.comments,
        )


class AuditLogOut(BaseModel):
    id: int
    content_id: int
    auditor_id: int
    audit_status: str
    audit_comments: str | None
    audit_time: str

    @classmethod
    def from_domain(cls, output: AuditLogOutput) -> AuditLogOut:
        """Construct HTTP response from domain output."""
        return cls(
            id=output.id,
            content_id=output.content_id,
            auditor_id=output.auditor_id,
            audit_status=output.audit_status,
            audit_comments=output.audit_comments,
            audit_time=output.audit_time,
        )


class SearchQueryIn(BaseModel):
    query: str
    limit: int = 10
    content_type: str | None = None

    def to_domain(self) -> SearchContentCommand:
        """Convert HTTP request to domain command."""
        return SearchContentCommand(
            query=self.query,
            limit=self.limit,
            content_type=self.content_type,
        )


class SearchResultOut(BaseModel):
    content: ContentOut
    score: float

    @classmethod
    def from_domain(cls, output: SearchResultOutput) -> SearchResultOut:
        """Construct HTTP response from domain output."""
        return cls(
            content=ContentOut.from_domain(output.content),
            score=output.score,
        )
