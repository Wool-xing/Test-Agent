"""Timeout hierarchy (§补-21) — unified timeout management.

Level 0: Global session timeout
Level 1: LLM call timeout
Level 2: Tool call timeout (per-tool)
Level 3: Test execution timeout (per-test)

Outer timeouts must exceed sum of inner timeouts.
Timeouts propagate downward: Level N expiry cancels all Level N+1 tasks.
"""

from __future__ import annotations

import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class TimeoutConfig:
    """Default timeout values (seconds)."""
    session_idle: float = 1800          # L0: 30min no interaction
    session_hard: float = 86400         # L0: 24h absolute max
    llm_request: float = 120            # L1: single LLM API call
    llm_first_token: float = 15         # L1: streaming first token
    llm_token_interval: float = 30      # L1: streaming token gap
    shell_exec: float = 60              # L2: shell tool (default)
    shell_exec_max: float = 300         # L2: shell tool (max)
    network_request: float = 30         # L2: network tool
    file_operation: float = 10          # L2: file read/write
    database_query: float = 15          # L2: database query
    test_execution: float = 300         # L3: per-test default


@dataclass
class TimeoutResult:
    """Result of a timeout-gated operation."""
    ok: bool
    timed_out: bool
    elapsed_ms: int
    result: Any = None
    error: str = ""


# Global config
_timeout_config = TimeoutConfig()


def get_timeout_config() -> TimeoutConfig:
    return _timeout_config


def set_timeout_config(config: TimeoutConfig) -> None:
    global _timeout_config
    _timeout_config = config


@contextmanager
def timeout_guard(seconds: float, label: str = "operation"):
    """Context manager that raises TimeoutError after `seconds`."""
    if seconds <= 0:
        yield
        return

    def _handler(signum, frame):
        raise TimeoutError(f"{label} timed out after {seconds}s")

    try:
        old = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(int(seconds))
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def run_with_timeout(fn: Callable, seconds: float, *args, **kwargs) -> TimeoutResult:
    """Execute fn with timeout. Returns TimeoutResult (cross-platform)."""
    start = time.monotonic()
    try:
        if seconds <= 0:
            result = fn(*args, **kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            return TimeoutResult(ok=True, timed_out=False, elapsed_ms=elapsed, result=result)

        import threading
        result_container = []
        error_container = []

        def _worker():
            try:
                result_container.append(fn(*args, **kwargs))
            except Exception as e:
                error_container.append(e)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=seconds)

        elapsed = int((time.monotonic() - start) * 1000)
        if thread.is_alive():
            return TimeoutResult(ok=False, timed_out=True, elapsed_ms=elapsed,
                                error=f"timed out after {seconds}s")
        if error_container:
            return TimeoutResult(ok=False, timed_out=False, elapsed_ms=elapsed,
                                error=str(error_container[0]))
        return TimeoutResult(ok=True, timed_out=False, elapsed_ms=elapsed,
                            result=result_container[0] if result_container else None)
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return TimeoutResult(ok=False, timed_out=False, elapsed_ms=elapsed, error=str(e))
