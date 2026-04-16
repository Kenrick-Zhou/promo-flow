"""Worker for scheduled hot score recalculation.

Runs daily at 3:00 AM via APScheduler to recalculate all content hot scores.
"""

from __future__ import annotations

import logging

from app.db.session import AsyncSessionLocal
from app.services.content.hot_score import update_all_hot_scores

logger = logging.getLogger(__name__)


async def refresh_all_hot_scores() -> None:
    """Recalculate hot scores for all contents (called by scheduler)."""
    logger.info("Starting daily hot score refresh")
    try:
        async with AsyncSessionLocal() as db:
            count = await update_all_hot_scores(db)
        logger.info("Daily hot score refresh completed: %d contents updated", count)
    except Exception:
        logger.exception("Daily hot score refresh failed")
