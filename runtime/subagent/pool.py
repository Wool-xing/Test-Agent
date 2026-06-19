"""Global ThreadPool for subagent tasks."""

from __future__ import annotations

import concurrent.futures
import os
import threading

from loguru import logger

_executor: concurrent.futures.ThreadPoolExecutor | None = None
_lock = threading.Lock()
_DEFAULT_WORKERS = min(32, (os.cpu_count() or 4))


def get_pool() -> concurrent.futures.ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = concurrent.futures.ThreadPoolExecutor(max_workers=_DEFAULT_WORKERS, thread_name_prefix="tagent-sub")
    return _executor


def resize_pool(max_workers: int) -> None:
    """Replace the pool with a new one sized to `max_workers`.

    Safe to call before tasks are submitted; existing tasks finish on the old pool.
    横切预算:避免大并发饥饿。
    """
    global _executor
    with _lock:
        old = _executor
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tagent-sub")
        if old is not None:
            old.shutdown(wait=False)
        logger.info("subagent pool resized to {}", max_workers)
