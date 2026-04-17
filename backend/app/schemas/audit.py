from __future__ import annotations

from pydantic import BaseModel, Field

from app.domains.content import (
    AuditContentCommand,
    AuditDecision,
    AuditLogOutput,
    EditContentMetadataCommand,
    ParsedQuery,
    SearchContentCommand,
    SearchOutput,
    SearchResultOutput,
    SearchTimingOutput,
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
    enable_rerank: bool | None = None

    def to_domain(self) -> SearchContentCommand:
        """Convert HTTP request to domain command."""
        return SearchContentCommand(
            query=self.query,
            limit=self.limit,
            content_type=self.content_type,
            enable_rerank=self.enable_rerank,
        )


class SearchResultItemOut(BaseModel):
    content: ContentOut
    final_score: float
    lexical_score: float
    semantic_score: float
    matched_signals: list[str]
    reranked: bool

    @classmethod
    def from_domain(cls, output: SearchResultOutput) -> SearchResultItemOut:
        """Construct HTTP response from domain output."""
        return cls(
            content=ContentOut.from_domain(output.content),
            final_score=output.final_score,
            lexical_score=output.lexical_score,
            semantic_score=output.semantic_score,
            matched_signals=output.matched_signals,
            reranked=output.reranked,
        )


class SearchTimingOut(BaseModel):
    query_parse_ms: float
    vector_recall_ms: float
    fts_recall_ms: float
    tag_recall_ms: float
    rrf_merge_ms: float
    scoring_ms: float
    llm_rerank_ms: float | None
    total_ms: float

    @classmethod
    def from_domain(cls, timing: SearchTimingOutput) -> SearchTimingOut:
        return cls(
            query_parse_ms=timing.query_parse_ms,
            vector_recall_ms=timing.vector_recall_ms,
            fts_recall_ms=timing.fts_recall_ms,
            tag_recall_ms=timing.tag_recall_ms,
            rrf_merge_ms=timing.rrf_merge_ms,
            scoring_ms=timing.scoring_ms,
            llm_rerank_ms=timing.llm_rerank_ms,
            total_ms=timing.total_ms,
        )


class ParsedQueryOut(BaseModel):
    parsed_content_type: str | None
    must_terms: list[str]
    should_terms: list[str]
    llm_used: bool
    sort_intent: str | None
    time_intent: dict[str, str | int] | None
    exclude_terms: list[str]
    limit_intent: int | None

    @classmethod
    def from_domain(cls, parsed: ParsedQuery) -> ParsedQueryOut:
        return cls(
            parsed_content_type=parsed.parsed_content_type,
            must_terms=parsed.must_terms,
            should_terms=parsed.should_terms,
            llm_used=parsed.llm_used,
            sort_intent=parsed.sort_intent,
            time_intent=parsed.time_intent,
            exclude_terms=parsed.exclude_terms,
            limit_intent=parsed.limit_intent,
        )


class SearchResultsOut(BaseModel):
    results: list[SearchResultItemOut]
    timing: SearchTimingOut | None = None
    query_info: ParsedQueryOut | None = None

    @classmethod
    def from_domain(cls, output: SearchOutput) -> SearchResultsOut:
        return cls(
            results=[SearchResultItemOut.from_domain(r) for r in output.results],
            timing=(
                SearchTimingOut.from_domain(output.timing) if output.timing else None
            ),
            query_info=(
                ParsedQueryOut.from_domain(output.query_info)
                if output.timing is not None
                else None
            ),
        )


# Legacy alias for backward compatibility
class SearchResultOut(BaseModel):
    content: ContentOut
    score: float

    @classmethod
    def from_legacy(cls, output: SearchResultOutput) -> SearchResultOut:
        """Construct from new domain output for backward compatibility."""
        return cls(
            content=ContentOut.from_domain(output.content),
            score=output.final_score,
        )


class ContentMetadataEditIn(BaseModel):
    title: str | None = Field(None, max_length=256)
    ai_summary: str | None = None

    def to_domain(self, *, content_id: int) -> EditContentMetadataCommand:
        """Convert HTTP request to domain command."""
        return EditContentMetadataCommand(
            content_id=content_id,
            title=self.title,
            ai_summary=self.ai_summary,
        )
