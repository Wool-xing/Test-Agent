"""Spawn isolated subagent tasks; fork-and-join API."""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger

from runtime.subagent.aux_client import aux_client
from runtime.subagent.pool import get_pool


@dataclass(slots=True)
class SubagentResult:
    ok: bool
    payload: Any
    error: str | None = None
    elapsed_ms: int = 0


def spawn(task: Callable[..., Any], *args, **kwargs) -> concurrent.futures.Future:
    """Submit a callable to the subagent pool. Returns Future."""
    return get_pool().submit(task, *args, **kwargs)


def fanout(tasks: list[Callable[..., Any]], *, timeout: float = 600.0) -> list[SubagentResult]:
    """Run multiple subagent tasks in parallel; collect results in submission order.

    横切准则:
      - 失败隔离:任一子任务 crash 不影响其他
      - 测试预算:总 timeout 上限
    """
    import time

    pool = get_pool()
    futures = [pool.submit(t) for t in tasks]
    results: list[SubagentResult] = []
    deadline = time.monotonic() + timeout
    for f in futures:
        remaining = max(0.0, deadline - time.monotonic())
        start = time.monotonic()
        try:
            payload = f.result(timeout=remaining)
            elapsed = int((time.monotonic() - start) * 1000)
            results.append(SubagentResult(ok=True, payload=payload, elapsed_ms=elapsed))
        except Exception as e:  # noqa: BLE001
            elapsed = int((time.monotonic() - start) * 1000)
            logger.warning("subagent task failed: {}", e)
            results.append(SubagentResult(ok=False, payload=None, error=str(e), elapsed_ms=elapsed))
    return results


def spawn_routed_subrun(prompt: str) -> SubagentResult:
    """Spawn a subagent that routes + executes a sub-prompt via aux client.

    Returns final summary only; never leaks subagent's intermediate context.
    """
    import time

    def _run() -> dict:
        from runtime.api.parsers import parse_text
        from runtime.router.router import route

        client = aux_client()
        art = parse_text(prompt)
        decision = route(art, client=client, use_history=False)
        return {"target": decision.detected_target_type, "nodes": [n.name for n in decision.dag], "confidence": decision.confidence}

    fut = spawn(_run)
    start = time.monotonic()
    try:
        payload = fut.result(timeout=180)
        return SubagentResult(ok=True, payload=payload, elapsed_ms=int((time.monotonic() - start) * 1000))
    except Exception as e:  # noqa: BLE001
        return SubagentResult(ok=False, payload=None, error=str(e), elapsed_ms=int((time.monotonic() - start) * 1000))
