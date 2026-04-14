"""Backfill search_document and embedding_text for existing contents.

Usage (must run from backend/ directory):
    cd backend && uv run python ../scripts/backfill_search_documents.py --dry-run
    cd backend && uv run python ../scripts/backfill_search_documents.py
    cd backend && uv run python ../scripts/backfill_search_documents.py --content-id 42
    cd backend && uv run python ../scripts/backfill_search_documents.py --ai-status-filter completed
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import selectinload, joinedload  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import app.db.base  # noqa: F401 — ensures all ORM models are registered
from app.core.config import settings  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.content import Content  # noqa: E402
from app.services.search.document_builder import (  # noqa: E402
    build_embedding_text,
    build_embedding_text_fallback,
    build_search_document,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def _get_content_fields(content: Content) -> dict:
    """Extract fields needed for document building."""
    category = content.category
    return {
        "title": content.title,
        "description": content.description,
        "tag_names": [t.name for t in content.tag_objects],
        "ai_keywords": content.ai_keywords or [],
        "ai_summary": content.ai_summary,
        "category_name": category.name if category else None,
        "primary_category_name": (
            category.parent.name if category and category.parent else None
        ),
        "content_type": content.content_type,
    }


async def backfill(
    dry_run: bool = False,
    content_id: int | None = None,
    ai_status_filter: str | None = None,
    regenerate_embeddings: bool = False,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)

    success = 0
    failed = 0
    skipped = 0

    generate_embedding = None
    if regenerate_embeddings:
        from app.services.infrastructure.ai import generate_embedding as _gen_emb

        generate_embedding = _gen_emb

    async with AsyncSession(engine) as db:
        stmt = (
            select(Content)
            .options(
                selectinload(Content.tag_objects),
                selectinload(Content.category).selectinload(Category.parent),
            )
            .order_by(Content.id)
        )

        if content_id is not None:
            stmt = stmt.where(Content.id == content_id)
        if ai_status_filter:
            stmt = stmt.where(Content.ai_status == ai_status_filter)

        result = await db.execute(stmt)
        all_contents = result.unique().scalars().all()

        total = len(all_contents)
        logger.info("Found %d contents to process", total)

        for i in range(0, total, BATCH_SIZE):
            batch = all_contents[i : i + BATCH_SIZE]

            for content in batch:
                try:
                    fields = _get_content_fields(content)
                    search_doc = build_search_document(**fields)

                    # For embedding text, use full builder if AI completed, else fallback
                    if content.ai_status == "completed":
                        emb_text = build_embedding_text(**fields)
                    else:
                        emb_text_or_none = build_embedding_text_fallback(
                            title=fields["title"],
                            description=fields["description"],
                            tag_names=fields["tag_names"],
                            category_name=fields["category_name"],
                            primary_category_name=fields["primary_category_name"],
                            content_type=fields["content_type"],
                        )
                        if emb_text_or_none is None:
                            skipped += 1
                            continue
                        emb_text = emb_text_or_none

                    if dry_run:
                        logger.info(
                            "[DRY RUN] content_id=%d search_doc=%s... emb_text=%s...",
                            content.id,
                            search_doc[:80],
                            emb_text[:80],
                        )
                        success += 1
                        continue

                    content.search_document = search_doc
                    content.embedding_text = emb_text

                    if regenerate_embeddings and generate_embedding:
                        embedding = await generate_embedding(emb_text)
                        content.embedding = embedding

                    success += 1
                except Exception:
                    logger.exception(
                        "Failed to process content_id=%d", content.id
                    )
                    failed += 1

            if not dry_run:
                await db.commit()
                logger.info("Committed batch %d-%d", i, min(i + BATCH_SIZE, total))

    await engine.dispose()
    logger.info(
        "Done. success=%d failed=%d skipped=%d total=%d",
        success,
        failed,
        skipped,
        total,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill search_document and embedding_text for contents"
    )
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")
    parser.add_argument("--content-id", type=int, help="Process a single content")
    parser.add_argument(
        "--ai-status-filter",
        choices=["completed", "failed", "pending", "processing"],
        help="Only process contents with this AI status",
    )
    parser.add_argument(
        "--regenerate-embeddings",
        action="store_true",
        help="Also regenerate embedding vectors",
    )
    args = parser.parse_args()

    asyncio.run(
        backfill(
            dry_run=args.dry_run,
            content_id=args.content_id,
            ai_status_filter=args.ai_status_filter,
            regenerate_embeddings=args.regenerate_embeddings,
        )
    )


if __name__ == "__main__":
    main()
