"""回填已有素材的原始分辨率。

用途：
  - 扫描 `contents` 表中尚未写入 `media_width` / `media_height` 的素材
  - 通过 OSS 访问原文件信息，提取图片/视频分辨率
  - 将结果回填到数据库

用法（在项目根目录执行）：
    uv run --directory backend python ../scripts/backfill_media_dimensions.py

常用参数：
    --dry-run        只检查，不写回数据库
    --limit 100      最多处理 100 条
    --batch-size 50  每批读取 50 条
    --force          即使已有分辨率也重新检查并覆盖
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import or_, select

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app.db.base  # noqa: F401,E402
from app.db import session as db_session  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.content import Content  # noqa: E402
from app.services.infrastructure.storage import (  # noqa: E402
    get_media_dimensions,
    get_public_url,
)


class Stats:
    def __init__(self) -> None:
        self.scanned = 0
        self.updated = 0
        self.skipped = 0
        self.failed = 0


def configure_logging() -> None:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    db_session.engine.echo = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填 contents 表中的素材分辨率")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检查素材分辨率，不写回数据库",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多处理多少条记录",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="每批读取多少条记录，默认 50",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使已有 media_width/media_height 也重新检查并覆盖",
    )
    return parser.parse_args()


def build_query(*, force: bool, last_seen_id: int, batch_size: int):
    stmt = (
        select(Content)
        .where(Content.id > last_seen_id)
        .order_by(Content.id)
        .limit(batch_size)
    )
    if force:
        return stmt
    return stmt.where(
        or_(Content.media_width.is_(None), Content.media_height.is_(None))
    )


async def process_batch(
    *,
    last_seen_id: int,
    batch_size: int,
    limit: int | None,
    force: bool,
    dry_run: bool,
    stats: Stats,
) -> tuple[int, int]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            build_query(
                force=force,
                last_seen_id=last_seen_id,
                batch_size=batch_size,
            )
        )
        items = result.scalars().all()

        if not items:
            return (0, last_seen_id)

        processed_in_batch = 0
        next_last_seen_id = last_seen_id
        for content in items:
            next_last_seen_id = content.id
            if limit is not None and stats.scanned >= limit:
                break

            stats.scanned += 1
            processed_in_batch += 1

            file_url = content.file_url or get_public_url(content.file_key)
            dims = await get_media_dimensions(file_url, content.content_type.value)

            if dims is None:
                stats.failed += 1
                print(
                    f"[FAIL] id={content.id} type={content.content_type.value} "
                    f"file_key={content.file_key} 无法获取分辨率"
                )
                continue

            width, height = dims
            changed = (
                content.media_width != width or content.media_height != height
            )

            if not changed:
                stats.skipped += 1
                print(
                    f"[SKIP] id={content.id} 已是 {width}x{height}，无需更新"
                )
                continue

            print(
                f"[OK] id={content.id} {content.content_type.value} -> {width}x{height}"
            )

            if dry_run:
                stats.updated += 1
                continue

            content.media_width = width
            content.media_height = height
            stats.updated += 1

        if not dry_run:
            await session.commit()

        return (processed_in_batch, next_last_seen_id)


async def main() -> None:
    configure_logging()
    args = parse_args()
    stats = Stats()
    last_seen_id = 0

    print("开始回填素材分辨率...")
    print(
        "参数: "
        f"dry_run={args.dry_run}, limit={args.limit}, "
        f"batch_size={args.batch_size}, force={args.force}"
    )

    while True:
        processed, last_seen_id = await process_batch(
            last_seen_id=last_seen_id,
            batch_size=args.batch_size,
            limit=args.limit,
            force=args.force,
            dry_run=args.dry_run,
            stats=stats,
        )
        if processed == 0:
            break
        if args.limit is not None and stats.scanned >= args.limit:
            break

    print("\n回填完成：")
    print(f"- 扫描: {stats.scanned}")
    print(f"- 更新: {stats.updated}")
    print(f"- 跳过: {stats.skipped}")
    print(f"- 失败: {stats.failed}")


if __name__ == "__main__":
    asyncio.run(main())
