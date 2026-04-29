"""Content CRUD service."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.domains.content import (
    AiStatus,
    AuditContentCommand,
    AuditDecision,
    AuditLogOutput,
    BatchCreateContentCommand,
    ContentListOutput,
    ContentOutput,
    ContentStatus,
    ContentType,
    CreateContentCommand,
    EditContentMetadataCommand,
    UpdateContentCommand,
)
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.models.content import Content
from app.models.tag import Tag
from app.prompts import render
from app.services.content.errors import (
    ContentForbiddenError,
    ContentNotFoundError,
    InvalidAuditActionError,
    InvalidCategoryError,
)
from app.services.infrastructure.storage import get_public_url

# Eager-loading options for Content queries
_CONTENT_LOAD_OPTIONS = [
    selectinload(Content.tag_objects),
    joinedload(Content.category).joinedload(Category.parent),
    joinedload(Content.uploader),
]


def _content_to_output(content: Content) -> ContentOutput:
    """Convert ORM Content to domain output."""
    category = content.category
    return ContentOutput(
        id=content.id,
        title=content.title,
        description=content.description,
        tags=[t.name for t in content.tag_objects],
        content_type=ContentType(content.content_type),
        status=ContentStatus(content.status),
        file_key=content.file_key,
        file_url=content.file_url or get_public_url(content.file_key),
        file_size=content.file_size,
        media_width=content.media_width,
        media_height=content.media_height,
        thumbnail_key=content.thumbnail_key,
        thumbnail_url=(
            get_public_url(content.thumbnail_key) if content.thumbnail_key else None
        ),
        view_count=content.view_count,
        download_count=content.download_count,
        ai_summary=content.ai_summary,
        ai_keywords=content.ai_keywords or [],
        ai_status=AiStatus(content.ai_status),
        ai_error=content.ai_error,
        ai_processed_at=(
            str(content.ai_processed_at) if content.ai_processed_at else None
        ),
        uploaded_by=content.uploaded_by,
        uploaded_by_name=content.uploader.name if content.uploader else "未知",
        category_id=content.category_id,
        category_name=category.name if category else None,
        primary_category_name=(
            category.parent.name if category and category.parent else None
        ),
        created_at=str(content.created_at),
        updated_at=str(content.updated_at),
    )


def _format_markdown_list(items: list[str], *, empty_text: str = "暂无") -> str:
    """Render a compact markdown-friendly list."""
    values = [item.strip() for item in items if item and item.strip()]
    if not values:
        return empty_text
    return "、".join(values)


def _build_template_kwargs(content: ContentOutput) -> dict:
    """Shared template variables for content announcement templates."""
    category_path = " / ".join(
        part
        for part in [content.primary_category_name, content.category_name]
        if part and part.strip()
    )
    return {
        "title": (content.title or "未命名素材").strip() or "未命名素材",
        "content_type_label": (
            "图片" if content.content_type == ContentType.image else "视频"
        ),
        "category_path": category_path or "暂未分类",
        "tags_text": _format_markdown_list(content.tags),
        "ai_keywords_text": _format_markdown_list(content.ai_keywords),
        "ai_summary": (content.ai_summary or "").strip() or "暂未生成 AI 摘要",
        "uploaded_by_name": (content.uploaded_by_name or "未知").strip() or "未知",
    }


def _render_download_intro_markdown(content: ContentOutput) -> str:
    """Render the pre-download intro shown to the user."""
    return render(
        "download_content_intro.j2",
        **_build_template_kwargs(content),
        view_count=content.view_count,
        download_count=content.download_count,
    ).strip()


def render_group_approved_markdown(content: ContentOutput) -> str:
    """Render the group chat announcement for a newly approved content."""
    return render(
        "group_content_approved.j2",
        **_build_template_kwargs(content),
    ).strip()


async def _find_or_create_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    """Find existing tags or create new ones by name."""
    if not names:
        return []
    # Strip whitespace and deduplicate while preserving order
    unique_names = list(dict.fromkeys(n.strip() for n in names if n.strip()))
    if not unique_names:
        return []

    result = await db.execute(select(Tag).where(Tag.name.in_(unique_names)))
    existing = {t.name: t for t in result.scalars().all()}

    tags = []
    for name in unique_names:
        if name in existing:
            tags.append(existing[name])
        else:
            tag = Tag(name=name, is_system=False)
            db.add(tag)
            tags.append(tag)

    if any(t.id is None for t in tags):
        await db.flush()  # Ensure new tags get IDs

    return tags


async def create_content(
    db: AsyncSession,
    *,
    command: CreateContentCommand,
) -> ContentOutput:
    """Create new content record."""
    # Validate category exists and is a secondary (child) category
    category = await db.get(Category, command.category_id)
    if category is None:
        raise InvalidCategoryError("指定的类目不存在。")
    if category.parent_id is None:
        raise InvalidCategoryError("素材必须归属到二级类目。")

    # Find or create tags
    tags = await _find_or_create_tags(db, command.tag_names)

    content = Content(
        title=command.title,
        description=command.description,
        content_type=command.content_type,
        file_key=command.file_key,
        file_url=get_public_url(command.file_key),
        uploaded_by=command.uploaded_by,
        category_id=command.category_id,
    )
    content.tag_objects = tags
    db.add(content)
    await db.flush()
    content_id = content.id
    await db.commit()
    # Re-query with full relationship loading
    return await get_content(db, content_id)


async def create_content_batch(
    db: AsyncSession,
    *,
    command: BatchCreateContentCommand,
) -> list[ContentOutput]:
    """Create multiple content records that share category, tags and description.

    Each file becomes its own Content row; the shared metadata is duplicated
    onto every row so downstream features (audit, search, AI) work uniformly.
    """
    if not command.items:
        raise InvalidCategoryError("批量上传至少需要一个文件。")

    # Validate category once (shared across all items)
    category = await db.get(Category, command.category_id)
    if category is None:
        raise InvalidCategoryError("指定的类目不存在。")
    if category.parent_id is None:
        raise InvalidCategoryError("素材必须归属到二级类目。")

    # Resolve tags once (shared across all items)
    tags = await _find_or_create_tags(db, command.tag_names)

    contents: list[Content] = []
    for item in command.items:
        content = Content(
            title=None,
            description=command.description,
            content_type=item.content_type,
            file_key=item.file_key,
            file_url=get_public_url(item.file_key),
            uploaded_by=command.uploaded_by,
            category_id=command.category_id,
        )
        content.tag_objects = list(tags)
        db.add(content)
        contents.append(content)

    await db.flush()
    content_ids = [c.id for c in contents]
    await db.commit()

    return [await get_content(db, cid) for cid in content_ids]


async def get_content(db: AsyncSession, content_id: int) -> ContentOutput:
    """Fetch a single content by ID. Raises ContentNotFoundError if not found."""
    result = await db.execute(
        select(Content).where(Content.id == content_id).options(*_CONTENT_LOAD_OPTIONS)
    )
    content = result.unique().scalars().first()
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    return _content_to_output(content)


async def get_content_orm(db: AsyncSession, content_id: int) -> Content:
    """Internal: fetch ORM Content by ID. Raises ContentNotFoundError if not found."""
    result = await db.execute(
        select(Content).where(Content.id == content_id).options(*_CONTENT_LOAD_OPTIONS)
    )
    content = result.unique().scalars().first()
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    return content


async def list_contents(
    db: AsyncSession,
    *,
    status: ContentStatus | None = None,
    content_type: ContentType | None = None,
    uploaded_by: int | None = None,
    category_id: int | None = None,
    primary_category_id: int | None = None,
    sort_by: str = "latest",
    offset: int = 0,
    limit: int = 20,
) -> ContentListOutput:
    """List contents with filtering and pagination."""
    stmt = select(Content).options(*_CONTENT_LOAD_OPTIONS)
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
    if category_id is not None:
        stmt = stmt.where(Content.category_id == category_id)
        count_stmt = count_stmt.where(Content.category_id == category_id)
    if primary_category_id is not None:
        # Filter by primary category: match content whose category's parent
        subq = (
            select(Category.id)
            .where(Category.parent_id == primary_category_id)
            .scalar_subquery()
        )
        stmt = stmt.where(Content.category_id.in_(subq))
        count_stmt = count_stmt.where(Content.category_id.in_(subq))

    total = (await db.execute(count_stmt)).scalar_one()

    order_clause = (
        Content.hot_score.desc() if sort_by == "hot" else Content.created_at.desc()
    )
    items = (
        (await db.execute(stmt.offset(offset).limit(limit).order_by(order_clause)))
        .unique()
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
    if command.tag_names is not None:
        content.tag_objects = await _find_or_create_tags(db, command.tag_names)
    if command.category_id is not None:
        # Validate category
        category = await db.get(Category, command.category_id)
        if category is None:
            raise InvalidCategoryError("指定的类目不存在。")
        if category.parent_id is None:
            raise InvalidCategoryError("素材必须归属到二级类目。")
        content.category_id = command.category_id

    await db.commit()
    return await get_content(db, content_id)


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
    title: str,
    summary: str,
    keywords: list[str],
    embedding: list[float],
    search_document: str | None = None,
    embedding_text: str | None = None,
) -> None:
    """Update AI-generated fields on content."""
    from datetime import datetime

    content = await db.get(Content, content_id)
    if content is None:
        return
    if title:
        content.title = title
    content.ai_summary = summary
    content.ai_keywords = keywords
    content.embedding = embedding
    content.ai_status = AiStatus.completed
    content.ai_error = None
    content.ai_processed_at = datetime.now(UTC)
    if search_document is not None:
        content.search_document = search_document
    if embedding_text is not None:
        content.embedding_text = embedding_text
    await db.commit()


async def mark_content_ai_failed(
    db: AsyncSession,
    content_id: int,
    *,
    error: str,
) -> None:
    """Mark AI processing as failed."""
    from datetime import datetime

    content = await db.get(Content, content_id)
    if content is None:
        return
    content.ai_status = AiStatus.failed
    content.ai_error = error
    content.ai_processed_at = datetime.now(UTC)
    await db.commit()


async def mark_content_ai_processing(
    db: AsyncSession,
    content_id: int,
) -> None:
    """Mark content AI status as processing."""
    content = await db.get(Content, content_id)
    if content is None:
        return
    content.ai_status = AiStatus.processing
    await db.commit()


async def update_content_media_dimensions(
    db: AsyncSession,
    content_id: int,
    *,
    width: int,
    height: int,
) -> None:
    """Update media width/height on content."""
    content = await db.get(Content, content_id)
    if content is None:
        return
    content.media_width = width
    content.media_height = height
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


async def edit_content_metadata(
    db: AsyncSession,
    *,
    command: EditContentMetadataCommand,
) -> ContentOutput:
    """Allow reviewer/admin to edit pending content metadata.

    Supports updating title, ai_summary, tags, ai_keywords, category and
    (for videos) a custom thumbnail object key. All fields are optional.
    """
    content = await get_content_orm(db, command.content_id)
    if command.title is not None:
        content.title = command.title
    if command.description is not None:
        content.description = command.description
    if command.ai_summary is not None:
        content.ai_summary = command.ai_summary
    if command.ai_keywords is not None:
        content.ai_keywords = command.ai_keywords
    if command.tag_names is not None:
        content.tag_objects = await _find_or_create_tags(db, command.tag_names)
    if command.category_id is not None:
        category = await db.get(Category, command.category_id)
        if category is None:
            raise InvalidCategoryError("指定的类目不存在。")
        if category.parent_id is None:
            raise InvalidCategoryError("素材必须归属到二级类目。")
        content.category_id = command.category_id
    if command.thumbnail_key is not None:
        content.thumbnail_key = command.thumbnail_key or None
    await db.commit()
    return await get_content(db, command.content_id)


async def reindex_content_search(db: AsyncSession, content_id: int) -> None:
    """Rebuild search_document, embedding_text and embedding for a content.

    Called after metadata edits so that searches reflect updated fields. Uses
    current persisted values; safe to skip if AI analysis has not run yet.
    """
    import logging

    from app.services.infrastructure.ai import generate_embedding
    from app.services.search.document_builder import (
        build_embedding_text,
        build_search_document,
    )

    logger = logging.getLogger(__name__)

    content = await get_content_orm(db, content_id)
    title = content.title
    description = content.description
    tag_names = [t.name for t in content.tag_objects]
    ai_keywords = list(content.ai_keywords or [])
    ai_summary = content.ai_summary
    category = content.category
    category_name = category.name if category else None
    primary_category_name = (
        category.parent.name if category and category.parent else None
    )
    content_type = (
        content.content_type.value
        if hasattr(content.content_type, "value")
        else str(content.content_type)
    )

    search_doc = build_search_document(
        title=title,
        description=description,
        tag_names=tag_names,
        ai_keywords=ai_keywords,
        ai_summary=ai_summary,
        category_name=category_name,
        primary_category_name=primary_category_name,
        content_type=content_type,
    )
    emb_text = build_embedding_text(
        title=title,
        description=description,
        tag_names=tag_names,
        ai_keywords=ai_keywords,
        ai_summary=ai_summary,
        category_name=category_name,
        primary_category_name=primary_category_name,
        content_type=content_type,
    )

    content.search_document = search_doc
    content.embedding_text = emb_text

    if emb_text.strip():
        try:
            embedding = await generate_embedding(emb_text)
            content.embedding = embedding
        except Exception:
            logger.exception(
                "Failed to regenerate embedding for content %s", content_id
            )

    await db.commit()


async def increment_view_count(db: AsyncSession, content_id: int) -> None:
    """Increment view count by 1."""
    content = await db.get(Content, content_id)
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    content.view_count = content.view_count + 1
    await db.commit()


async def increment_download_count(db: AsyncSession, content_id: int) -> None:
    """Increment download count by 1."""
    content = await db.get(Content, content_id)
    if content is None:
        raise ContentNotFoundError(content_id=content_id)
    content.download_count = content.download_count + 1
    await db.commit()


async def send_file_to_user(
    content_id: int,
    *,
    feishu_open_id: str,
) -> None:
    """Stream file from OSS into a SpooledTemporaryFile then DM via Feishu bot.

    SpooledTemporaryFile buffers up to 10 MB in memory; larger files spill to
    disk automatically.  The result is always seekable, satisfying the
    requests_toolbelt MultipartEncoder requirement.
    """
    import asyncio
    import logging
    import tempfile

    import httpx

    from app.db.session import AsyncSessionLocal
    from app.services.infrastructure.feishu import (
        send_file_to_user_sync as _feishu_send_file_sync,
    )
    from app.services.infrastructure.feishu import (
        send_image_to_user_sync as _feishu_send_image_sync,
    )
    from app.services.infrastructure.feishu import (
        send_markdown_to_user as _feishu_send_markdown,
    )

    logger = logging.getLogger("promoflow.api")
    logger.info(
        "send_file_to_user start: content=%s open_id=%s", content_id, feishu_open_id
    )

    def _stream_oss_to_feishu(
        file_url: str,
        target_id: str,
        file_name: str,
        is_image: bool,
        *,
        send_image,
        send_file,
    ) -> None:
        """Sync: stream OSS → seekable SpooledTemporaryFile → Feishu SDK."""
        with httpx.Client(timeout=120.0) as http:
            with http.stream("GET", file_url) as resp:
                resp.raise_for_status()
                logger.info(
                    "OSS stream open: status=%s content-length=%s",
                    resp.status_code,
                    resp.headers.get("content-length", "unknown"),
                )
                # SpooledTemporaryFile: ≤10 MB stays in RAM, larger spills to disk.
                # Always seekable — satisfies requests_toolbelt MultipartEncoder.
                with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as tmp:
                    for chunk in resp.iter_bytes(65536):
                        tmp.write(chunk)
                    tmp.seek(0)
                    if is_image:
                        send_image(target_id, tmp, file_name)
                    else:
                        send_file(target_id, tmp, file_name)

    async def _load_delivery_payload() -> tuple[str, str, bool, str]:
        async with AsyncSessionLocal() as db:
            content = await get_content_orm(db, content_id)
            content_output = _content_to_output(content)

        file_url = content.file_url or get_public_url(content.file_key)
        file_name = content.file_key.rsplit("/", 1)[-1]
        is_image = content.content_type == ContentType.image
        intro_markdown = _render_download_intro_markdown(content_output)
        return file_url, file_name, is_image, intro_markdown

    try:
        file_url, file_name, is_image, intro_markdown = await _load_delivery_payload()

        try:
            await _feishu_send_markdown(
                feishu_open_id,
                title="素材已开始准备",
                markdown=intro_markdown,
            )
        except Exception:
            logger.exception(
                "Failed to send download intro to user %s for content %s",
                feishu_open_id,
                content_id,
            )

        await asyncio.to_thread(
            lambda: _stream_oss_to_feishu(
                file_url,
                feishu_open_id,
                file_name,
                is_image,
                send_image=_feishu_send_image_sync,
                send_file=_feishu_send_file_sync,
            )
        )
    except Exception:
        logger.exception(
            "Failed to send file to user %s for content %s", feishu_open_id, content_id
        )


async def send_file_to_chat(
    content_id: int,
    *,
    chat_id: str,
) -> None:
    """Stream file from OSS and send intro card + file to the current group chat."""
    import asyncio
    import logging
    import tempfile

    import httpx

    from app.db.session import AsyncSessionLocal
    from app.services.infrastructure.feishu import (
        send_file_to_chat_sync as _feishu_send_file_to_chat_sync,
    )
    from app.services.infrastructure.feishu import (
        send_image_to_chat_sync as _feishu_send_image_to_chat_sync,
    )
    from app.services.infrastructure.feishu import (
        send_interactive_card_to_chat as _feishu_send_card_to_chat,
    )

    logger = logging.getLogger("promoflow.api")
    logger.info("send_file_to_chat start: content=%s chat_id=%s", content_id, chat_id)

    def _stream_oss_to_feishu(
        file_url: str,
        target_id: str,
        file_name: str,
        is_image: bool,
    ) -> None:
        with httpx.Client(timeout=120.0) as http:
            with http.stream("GET", file_url) as resp:
                resp.raise_for_status()
                logger.info(
                    "OSS stream open: status=%s content-length=%s",
                    resp.status_code,
                    resp.headers.get("content-length", "unknown"),
                )
                with tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024) as tmp:
                    for chunk in resp.iter_bytes(65536):
                        tmp.write(chunk)
                    tmp.seek(0)
                    if is_image:
                        _feishu_send_image_to_chat_sync(target_id, tmp, file_name)
                    else:
                        _feishu_send_file_to_chat_sync(target_id, tmp, file_name)

    try:
        async with AsyncSessionLocal() as db:
            content = await get_content_orm(db, content_id)
            content_output = _content_to_output(content)

        file_url = content.file_url or get_public_url(content.file_key)
        file_name = content.file_key.rsplit("/", 1)[-1]
        is_image = content.content_type == ContentType.image
        intro_markdown = _render_download_intro_markdown(content_output)

        try:
            await _feishu_send_card_to_chat(
                chat_id,
                title="素材已开始准备",
                markdown=intro_markdown,
            )
        except Exception:
            logger.exception(
                "Failed to send download intro to chat %s for content %s",
                chat_id,
                content_id,
            )

        await asyncio.to_thread(
            _stream_oss_to_feishu,
            file_url,
            chat_id,
            file_name,
            is_image,
        )
    except Exception:
        logger.exception(
            "Failed to send file to chat %s for content %s", chat_id, content_id
        )
