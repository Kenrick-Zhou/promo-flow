"""Hot score calculation and update service."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Content

logger = logging.getLogger(__name__)


def calculate_hot_score(
    views: int,
    downloads: int,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> float:
    """Calculate hot score for a single content item.

    Formula:
        (log(views * view_weight + 1) + log(downloads * download_weight + 1))
        * freshness * time_decay

    Where:
        freshness = (-atan(0.5 * (age_days - N)) + pi/2) / pi
        time_decay = e^(-lambda * age_days)
    """
    if now is None:
        now = datetime.now(UTC)

    view_weight = settings.HOT_SCORE_VIEW_WEIGHT
    download_weight = settings.HOT_SCORE_DOWNLOAD_WEIGHT
    n = settings.HOT_SCORE_FRESHNESS_HALF_LIFE_DAYS
    decay_lambda = settings.HOT_SCORE_TIME_DECAY_LAMBDA

    age_days = max((now - created_at).total_seconds() / 86400, 0)

    engagement = math.log(views * view_weight + 1) + math.log(
        downloads * download_weight + 1
    )
    freshness = (-math.atan(0.5 * (age_days - n)) + math.pi / 2) / math.pi
    time_decay = math.exp(-decay_lambda * age_days)

    return engagement * freshness * time_decay


async def update_hot_score(db: AsyncSession, content_id: int) -> None:
    """Recalculate and persist hot score for a single content."""
    content = await db.get(Content, content_id)
    if content is None:
        return

    now = datetime.now(UTC)
    content.hot_score = calculate_hot_score(
        content.view_count,
        content.download_count,
        content.created_at,
        now=now,
    )
    content.hot_score_updated_at = now
    await db.commit()


async def update_all_hot_scores(db: AsyncSession, *, batch_size: int = 50) -> int:
    """Recalculate hot scores for all contents in batches.

    Returns the number of contents updated.
    """
    now = datetime.now(UTC)
    result = await db.execute(select(Content.id))
    all_ids = [row[0] for row in result.all()]

    updated = 0
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i : i + batch_size]
        batch_result = await db.execute(
            select(Content).where(Content.id.in_(batch_ids))
        )
        contents = batch_result.scalars().all()

        for content in contents:
            content.hot_score = calculate_hot_score(
                content.view_count,
                content.download_count,
                content.created_at,
                now=now,
            )
            content.hot_score_updated_at = now
            updated += 1

        await db.commit()

    logger.info("Hot score batch update completed: %d contents updated", updated)
    return updated
