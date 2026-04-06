"""Content CRUD service."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.content import (
    AuditContentCommand,
    AuditDecision,
    AuditLogOutput,
    ContentListOutput,
    ContentOutput,
    ContentStatus,
    ContentType,
    CreateContentCommand,
    UpdateContentCommand,
)
from app.models.audit_log import AuditLog
from app.models.content import Content
from app.services.content.errors import (
    ContentForbiddenError,
    ContentNotFoundError,
    InvalidAuditActionError,
)


def _content_to_output(content: Content) -> ContentOutput:
    """Convert ORM Content to domain output."""
    return ContentOutput(
        id=content.id,
        title=content.title,
        description=content.description,
        tags=content.tags or [],
        content_type=ContentType(content.content_type),
        status=ContentStatus(content.status),
        file_key=content.file_key,
        file_url=content.file_url,
        file_size=content.file_size,
        ai_summary=content.ai_summary,
        ai_keywords=content.ai_keywords or [],
        uploaded_by=content.uploaded_by,
        created_at=str(content.created_at),
        updated_at=str(content.updated_at),
    )


async def create_content(
    db: AsyncSession,
    *,
    command: CreateContentCommand,
) -> ContentOutput:
    """Create new content record."""
    content = Content(
        title=command.title,
        description=command.description,
        tags=command.tags,
        content_type=command.content_type,
        file_key=command.file_key,
        uploaded_by=command.uploaded_by,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return _content_to_output(content)


async def get_content(db: AsyncSession, content_id: int) -> ContentOutput:
    """Fetch a single content by ID. Raises ContentNotFoundError if not found."""
    content = await db.get(Content, content_id)
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    return _content_to_output(content)


async def get_content_orm(db: AsyncSession, content_id: int) -> Content:
    """Internal: fetch ORM Content by ID. Raises ContentNotFoundError if not found."""
    content = await db.get(Content, content_id)
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    return content


async def list_contents(
    db: AsyncSession,
    *,
    status: ContentStatus | None = None,
    content_type: ContentType | None = None,
    uploaded_by: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> ContentListOutput:
    """List contents with filtering and pagination."""
    stmt = select(Content)
    count_stmt = select(func.count()).select_from(Content)

    if status:
        stmt = stmt.where(Content.status == status)
        count_stmt = count_stmt.where(Content.status == status)
    if content_type:
        stmt = stmt.where(Content.content_type == content_type)
        count_stmt = count_stmt.where(Content.content_type == content_type)
    if uploaded_by:
        stmt = stmt.where(Content.uploaded_by == uploaded_by)
        count_stmt = count_stmt.where(Content.uploaded_by == uploaded_by)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (
        (
            await db.execute(
                stmt.offset(offset).limit(limit).order_by(Content.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ContentListOutput(
        total=total,
        items=[_content_to_output(c) for c in items],
    )


async def update_content(
    db: AsyncSession,
    content_id: int,
    *,
    command: UpdateContentCommand,
    user_id: int,
    user_role: str,
) -> ContentOutput:
    """Update content metadata. Checks ownership/permissions."""
    content = await get_content_orm(db, content_id)

    if content.uploaded_by != user_id and user_role not in ("reviewer", "admin"):
        raise ContentForbiddenError()

    if command.title is not None:
        content.title = command.title
    if command.description is not None:
        content.description = command.description
    if command.tags is not None:
        content.tags = command.tags

    await db.commit()
    await db.refresh(content)
    return _content_to_output(content)


async def delete_content(
    db: AsyncSession,
    content_id: int,
    *,
    user_id: int,
    user_role: str,
) -> str:
    """Delete content. Returns file_key for storage cleanup. Checks permissions."""
    content = await get_content_orm(db, content_id)

    if content.uploaded_by != user_id and user_role != "admin":
        raise ContentForbiddenError()

    file_key = content.file_key
    await db.delete(content)
    await db.commit()
    return file_key


async def update_content_ai_fields(
    db: AsyncSession,
    content_id: int,
    *,
    summary: str,
    keywords: list[str],
    embedding: list[float],
) -> None:
    """Update AI-generated fields on content."""
    content = await db.get(Content, content_id)
    if content is None:
        return
    content.ai_summary = summary
    content.ai_keywords = keywords
    content.embedding = embedding
    await db.commit()


async def audit_content(
    db: AsyncSession,
    *,
    command: AuditContentCommand,
) -> AuditLogOutput:
    """Audit (approve/reject) content."""
    if command.decision not in (AuditDecision.approved, AuditDecision.rejected):
        raise InvalidAuditActionError()

    content = await get_content_orm(db, command.content_id)
    content.status = (
        ContentStatus.approved
        if command.decision == AuditDecision.approved
        else ContentStatus.rejected
    )

    audit_log = AuditLog(
        content_id=command.content_id,
        auditor_id=command.auditor_id,
        audit_status=command.decision.value,
        audit_comments=command.comments,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)

    return AuditLogOutput(
        id=audit_log.id,
        content_id=audit_log.content_id,
        auditor_id=audit_log.auditor_id,
        audit_status=audit_log.audit_status,
        audit_comments=audit_log.audit_comments,
        audit_time=str(audit_log.audit_time),
    )
