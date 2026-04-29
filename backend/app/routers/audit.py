"""Audit routes: review pending content."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_role
from app.domains.content import AuditDecision, ContentStatus, UserRole
from app.models.user import User
from app.schemas.audit import AuditActionIn, AuditLogOut, ContentMetadataEditIn
from app.schemas.content import ContentListOut, ContentOut
from app.services.content import (
    ContentNotFoundError,
    InvalidAuditActionError,
    InvalidCategoryError,
    audit_content,
    edit_content_metadata,
    list_contents,
    raise_content_error,
)

router = APIRouter(prefix="/audit", tags=["audit"])

_reviewer_or_admin = require_role(UserRole.reviewer, UserRole.admin)


@router.get("/pending", response_model=ContentListOut)
async def list_pending(
    current_user: Annotated[User, Depends(_reviewer_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    offset: int = 0,
    limit: int = 20,
):
    result = await list_contents(
        db,
        status=ContentStatus.pending,
        offset=offset,
        limit=limit,
    )
    return ContentListOut(
        total=result.total,
        items=[ContentOut.from_domain(c) for c in result.items],
    )


@router.post("/{content_id}", response_model=AuditLogOut)
async def audit_content_route(
    content_id: int,
    action: AuditActionIn,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(_reviewer_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        output = await audit_content(
            db,
            command=action.to_domain(content_id=content_id, auditor_id=current_user.id),
        )
    except (ContentNotFoundError, InvalidAuditActionError) as exc:
        raise_content_error(exc)

    if action.status == AuditDecision.approved:
        from app.bot.handlers import notify_content_approved

        background_tasks.add_task(notify_content_approved, content_id)

    return AuditLogOut.from_domain(output)


@router.patch("/{content_id}/metadata", response_model=ContentOut)
async def edit_metadata_route(
    content_id: int,
    data: ContentMetadataEditIn,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(_reviewer_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Allow reviewer/admin to edit pending content metadata.

    Re-indexes the content (search_document + embedding) in the background
    so updated fields are reflected in subsequent searches.
    """
    try:
        output = await edit_content_metadata(
            db,
            command=data.to_domain(content_id=content_id),
        )
    except (ContentNotFoundError, InvalidCategoryError) as exc:
        raise_content_error(exc)

    background_tasks.add_task(_reindex_content_bg, output.id)
    return ContentOut.from_domain(output)


async def _reindex_content_bg(content_id: int) -> None:
    """Background task: rebuild search index + embedding after metadata edit."""
    import logging

    from app.db.session import AsyncSessionLocal
    from app.services.content import reindex_content_search

    logger = logging.getLogger(__name__)
    try:
        async with AsyncSessionLocal() as db:
            await reindex_content_search(db, content_id)
    except Exception:
        logger.exception("Failed to reindex content %d after edit", content_id)
