"""Content CRUD routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.domains.content import ContentStatus, ContentType, PresignedUrlOutput
from app.models.user import User
from app.schemas.content import (
    ContentCreateIn,
    ContentListOut,
    ContentOut,
    ContentUpdateIn,
    PresignedUrlOut,
)
from app.services.content import (
    ContentForbiddenError,
    ContentNotFoundError,
    InvalidCategoryError,
    create_content,
    delete_content,
    get_content,
    list_contents,
    raise_content_error,
    update_content,
)
from app.services.infrastructure.storage import (
    delete_object,
    generate_file_key,
    generate_presigned_upload_url,
    get_public_url,
)

router = APIRouter(prefix="/contents", tags=["content"])


@router.get("/presigned-upload", response_model=PresignedUrlOut)
async def get_presigned_upload_url_route(
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a presigned OSS PUT URL for direct browser upload."""
    file_key = generate_file_key(filename)
    upload_url = await generate_presigned_upload_url(file_key)
    return PresignedUrlOut.from_domain(
        PresignedUrlOutput(upload_url=upload_url, file_key=file_key)
    )


@router.post("", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
async def create_content_route(
    data: ContentCreateIn,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a newly uploaded file and trigger AI analysis in background."""
    try:
        output = await create_content(
            db,
            command=data.to_domain(uploaded_by=current_user.id),
        )
    except (ContentNotFoundError, ContentForbiddenError, InvalidCategoryError) as exc:
        raise_content_error(exc)

    background_tasks.add_task(
        _run_ai_analysis, output.id, output.file_key, output.content_type.value
    )
    return ContentOut.from_domain(output)


@router.get("", response_model=ContentListOut)
async def list_contents_route(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: ContentStatus | None = Query(None, alias="status"),
    content_type: ContentType | None = None,
    my_uploads: bool = False,
    offset: int = 0,
    limit: int = Query(20, le=100),
):
    uploaded_by = current_user.id if my_uploads else None
    result = await list_contents(
        db,
        status=status_filter,
        content_type=content_type,
        uploaded_by=uploaded_by,
        offset=offset,
        limit=limit,
    )
    return ContentListOut(
        total=result.total,
        items=[ContentOut.from_domain(c) for c in result.items],
    )


@router.get("/{content_id}", response_model=ContentOut)
async def get_content_route(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        output = await get_content(db, content_id)
    except ContentNotFoundError as exc:
        raise_content_error(exc)
    return ContentOut.from_domain(output)


@router.patch("/{content_id}", response_model=ContentOut)
async def update_content_route(
    content_id: int,
    data: ContentUpdateIn,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        output = await update_content(
            db,
            content_id,
            command=data.to_domain(),
            user_id=current_user.id,
            user_role=current_user.role.value,
        )
    except (ContentNotFoundError, ContentForbiddenError, InvalidCategoryError) as exc:
        raise_content_error(exc)
    return ContentOut.from_domain(output)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content_route(
    content_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        file_key = await delete_content(
            db,
            content_id,
            user_id=current_user.id,
            user_role=current_user.role.value,
        )
    except (ContentNotFoundError, ContentForbiddenError) as exc:
        raise_content_error(exc)
    await delete_object(file_key)


async def _run_ai_analysis(content_id: int, file_key: str, content_type: str) -> None:
    """Background task: analyze content with AI and update embedding."""
    from app.db.session import AsyncSessionLocal
    from app.services.content import update_content_ai_fields
    from app.services.infrastructure.ai import analyze_content, generate_embedding

    file_url = get_public_url(file_key)
    result = await analyze_content(file_url, content_type)
    summary = result.get("summary", "")
    keywords = result.get("keywords", [])
    embedding_text = f"{summary} {' '.join(keywords)}"
    embedding = await generate_embedding(embedding_text)

    async with AsyncSessionLocal() as db:
        await update_content_ai_fields(
            db, content_id, summary=summary, keywords=keywords, embedding=embedding
        )
