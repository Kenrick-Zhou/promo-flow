"""Schedule AI analysis tasks with a process-level concurrency limit.

`BackgroundTasks` 在单个请求内是顺序 await 的，导致批量上传时即使同时入队
多个 AI 分析任务，DB 中也只会出现一条 ``ai_status='processing'``。

本模块用 ``asyncio.create_task`` 让每个分析任务独立调度，并通过一个进程级
``asyncio.Semaphore`` 限制最大并发，避免打爆 DashScope QPS / 线程池。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_tasks: set[asyncio.Task[None]] = set()


def _get_semaphore() -> asyncio.Semaphore:
    """Lazily create the semaphore inside the running event loop."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.AI_ANALYSIS_CONCURRENCY)
    return _semaphore


def schedule_ai_task(
    coro_factory: Callable[[], Awaitable[None]],
    *,
    label: str,
) -> None:
    """Schedule an AI analysis coroutine with global concurrency control.

    ``coro_factory`` 必须是无参可调用对象，每次调用返回一个新的 coroutine——
    这样信号量 acquire 之前不会创建协程对象，避免 RuntimeWarning。
    """
    sem = _get_semaphore()

    async def _runner() -> None:
        async with sem:
            try:
                await coro_factory()
            except Exception:
                logger.exception("AI task failed: %s", label)

    task = asyncio.create_task(_runner(), name=f"ai-task:{label}")
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
