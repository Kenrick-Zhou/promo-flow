"""手动全量串行计算并更新所有内容的热度值。

用法（须在 backend/ 目录下运行）：
    cd backend && uv run python ../scripts/recalculate_hot_scores.py
    cd backend && uv run python ../scripts/recalculate_hot_scores.py --dry-run
    cd backend && uv run python ../scripts/recalculate_hot_scores.py --content-id 42
    cd backend && uv run python ../scripts/recalculate_hot_scores.py --batch-size 100
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend/ is on sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import app.db.base  # noqa: F401 — 确保所有 ORM 模型已注册
from app.core.config import settings  # noqa: E402
from app.models.content import Content  # noqa: E402
from app.services.content.hot_score import calculate_hot_score  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def recalculate(
    dry_run: bool = False,
    content_id: int | None = None,
    batch_size: int = 50,
) -> None:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    now = datetime.now(UTC)

    success = 0
    failed = 0

    async with AsyncSession(engine) as db:
        stmt = select(Content).order_by(Content.id)
        if content_id is not None:
            stmt = stmt.where(Content.id == content_id)

        result = await db.execute(stmt)
        all_contents = result.scalars().all()
        total = len(all_contents)

        logger.info(
            "Found %d content(s) to recalculate (batch_size=%d, dry_run=%s)",
            total,
            batch_size,
            dry_run,
        )
        logger.info(
            "Config: view_weight=%.1f, download_weight=%.1f, "
            "freshness_half_life_days=%.1f, time_decay_lambda=%.4f",
            settings.HOT_SCORE_VIEW_WEIGHT,
            settings.HOT_SCORE_DOWNLOAD_WEIGHT,
            settings.HOT_SCORE_FRESHNESS_HALF_LIFE_DAYS,
            settings.HOT_SCORE_TIME_DECAY_LAMBDA,
        )

        for i in range(0, total, batch_size):
            batch = all_contents[i : i + batch_size]

            for content in batch:
                try:
                    score = calculate_hot_score(
                        content.view_count,
                        content.download_count,
                        content.created_at,
                        now=now,
                    )
                    if dry_run:
                        logger.info(
                            "[DRY RUN] content_id=%d  views=%d  downloads=%d  "
                            "hot_score=%.6f  (prev=%.6f)",
                            content.id,
                            content.view_count,
                            content.download_count,
                            score,
                            content.hot_score,
                        )
                    else:
                        content.hot_score = score
                        content.hot_score_updated_at = now
                    success += 1
                except Exception:
                    logger.exception(
                        "Failed to calculate hot score for content_id=%d", content.id
                    )
                    failed += 1

            if not dry_run:
                await db.commit()
                logger.info(
                    "Committed batch %d/%d (%d contents)",
                    i // batch_size + 1,
                    (total + batch_size - 1) // batch_size,
                    len(batch),
                )

    logger.info(
        "Done. success=%d, failed=%d%s",
        success,
        failed,
        " [DRY RUN — no changes written]" if dry_run else "",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="手动全量串行计算并更新所有内容的热度值"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印计算结果，不写入数据库",
    )
    parser.add_argument(
        "--content-id",
        type=int,
        default=None,
        metavar="ID",
        help="只更新指定 content_id 的热度值",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        metavar="N",
        help="每批提交的条数（默认 50）",
    )
    args = parser.parse_args()
    asyncio.run(
        recalculate(
            dry_run=args.dry_run,
            content_id=args.content_id,
            batch_size=args.batch_size,
        )
    )


if __name__ == "__main__":
    main()
