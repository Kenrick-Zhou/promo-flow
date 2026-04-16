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
    current_user: Annotated[User, Depends(_reviewer_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Allow reviewer/admin to edit content title and/or AI summary."""
    try:
        output = await edit_content_metadata(
            db,
            command=data.to_domain(content_id=content_id),
        )
    except ContentNotFoundError as exc:
        raise_content_error(exc)
    return ContentOut.from_domain(output)
