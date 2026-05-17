"""Exponential-backoff retry wrapper for node / script execution."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from typing import TypeVar

from loguru import logger

from runtime.router.llm_client import LLMError

F = TypeVar("F", bound=Callable)

RETRYABLE = (subprocess.TimeoutExpired, RuntimeError, LLMError, OSError)
MAX_RETRIES = 3
BASE_BACKOFF = 2.0


def with_retry(func: F, max_retries: int = MAX_RETRIES, backoff: float = BASE_BACKOFF) -> F:
    """Wrap a callable with exponential‑backoff retry on transient failures.

    Catches: subprocess.TimeoutExpired, RuntimeError, LLMError, OSError.
    After *max_retries* attempts the original exception is re‑raised.
    """

    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RETRYABLE as exc:
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = backoff**attempt
                    logger.warning(
                        "retry {}/{} for {} after {:.1f}s: {}",
                        attempt + 1,
                        max_retries - 1,
                        getattr(func, "__name__", func),
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                else:
                    logger.error("all {} retries exhausted for {}: {}", max_retries, getattr(func, "__name__", func), exc)
        raise last_exc  # type: ignore[misc]

    wrapper.__name__ = getattr(func, "__name__", "retry_wrapper")
    wrapper.__doc__ = func.__doc__
    return wrapper  # type: ignore[return-value]
