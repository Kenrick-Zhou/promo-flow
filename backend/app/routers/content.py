"""Content CRUD routes."""

from __future__ import annotations

from typing import Annotated, TypedDict

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.domains.content import (
    ContentOutput,
    ContentStatus,
    ContentType,
    PresignedUrlOutput,
)
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


class _AiContext(TypedDict):
    primary_category_name: str | None
    category_name: str | None
    tags: list[str]
    description: str | None


def _build_ai_context(content: ContentOutput) -> _AiContext:
    """Build structured context passed into AI analysis/title generation."""
    return {
        "primary_category_name": content.primary_category_name,
        "category_name": content.category_name,
        "tags": content.tags,
        "description": content.description,
    }


@router.get("/presigned-upload", response_model=PresignedUrlOut)
async def get_presigned_upload_url_route(
    filename: str,
    current_user: Annotated[User, Depends(get_current_user)],
    content_type: str | None = None,
):
    """Get a presigned OSS PUT URL for direct browser upload."""
    file_key = generate_file_key(filename)
    upload_headers = {"Content-Type": content_type} if content_type else {}
    upload_url = await generate_presigned_upload_url(
        file_key,
        headers=upload_headers or None,
    )
    return PresignedUrlOut.from_domain(
        PresignedUrlOutput(
            upload_url=upload_url,
            file_key=file_key,
            upload_headers=upload_headers,
        )
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
    import logging

    from app.db.session import AsyncSessionLocal
    from app.services.content import (
        get_content,
        mark_content_ai_failed,
        mark_content_ai_processing,
        update_content_ai_fields,
    )
    from app.services.infrastructure.ai import (
        analyze_content,
        generate_content_title,
        generate_embedding,
    )

    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        await mark_content_ai_processing(db, content_id)
        content = await get_content(db, content_id)

    ai_context = _build_ai_context(content)

    try:
        file_url = get_public_url(file_key)
        result = await analyze_content(file_url, content_type, **ai_context)
        summary = result.get("summary", "")
        keywords = result.get("keywords", [])
        title = await generate_content_title(
            content_type,
            **ai_context,
            summary=summary,
            keywords=keywords,
        )
        parts = [p for p in [title, summary, " ".join(keywords)] if p]
        embedding_text = " ".join(parts)
        embedding = await generate_embedding(embedding_text)

        async with AsyncSessionLocal() as db:
            await update_content_ai_fields(
                db,
                content_id,
                title=title,
                summary=summary,
                keywords=keywords,
                embedding=embedding,
            )
    except Exception:
        logger.exception("AI analysis failed for content %s", content_id)
        async with AsyncSessionLocal() as db:
            await mark_content_ai_failed(
                db, content_id, error="AI 分析失败，请稍后重试"
            )
