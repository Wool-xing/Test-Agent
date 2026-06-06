"""IM → Agent bridge: process inbound chat messages through the test kernel.

Routes text from IM platforms through the same routing/dispatch pipeline
as the REPL, formats results as plain text, and sends replies back via
the existing gateway platform adapters.

Supports:
  - Direct agent/skill invocation (@agent-name or "用 agent-name")
  - Multi-turn conversation memory per IM user
  - Full LLM routing fallback for unstructured requests
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from loguru import logger

from runtime.api.deps import Kernel
from runtime.api.parsers import parse_text
from runtime.cli.conversation import ConversationMemory
from runtime.gateway.base import Message, get_platform
from runtime.router.intent import try_fast_path
from runtime.router.schema import RoutingDecision


@dataclass
class BridgeResult:
    ok: bool
    reply: str
    error: str | None = None


# Per-user conversation memory (LRU, max 100 concurrent users)
_MEMORIES: OrderedDict[str, ConversationMemory] = OrderedDict()
_MAX_MEMORIES = 100


def _memory_key(platform: str, user: str | None, target: str | None) -> str:
    return f"{platform}:{user or 'anon'}:{target or 'direct'}"


def _get_memory(key: str) -> ConversationMemory:
    if key not in _MEMORIES:
        if len(_MEMORIES) >= _MAX_MEMORIES:
            _MEMORIES.popitem(last=False)  # evict oldest
        _MEMORIES[key] = ConversationMemory()
    return _MEMORIES[key]


def _format_dag_summary(summary: dict[str, Any], max_nodes: int = 10) -> str:
    """Format a DAG execution summary as plain text (no Rich markup)."""
    total = summary["total"]
    succ = summary["succeeded"]
    fail = summary.get("failed", 0)
    lines = [f"🎯 Test-Agent · {succ}/{total} ok, {fail} failed"]

    results = summary.get("results", {})
    shown = 0
    for nid, r in results.items():
        if shown >= max_nodes:
            lines.append(f"  … +{len(results) - max_nodes} more")
            break
        status = "✅" if r.get("ok") else "❌"
        name = r.get("name", nid)[:40]
        dur = r.get("duration_ms", 0)
        dur_str = f" ({dur:.0f}ms)" if dur else ""
        lines.append(f"  {status} {name}{dur_str}")
        shown += 1

    if fail == 0:
        lines.append("\n✓ All checks passed.")
    return "\n".join(lines)


def _build_decision(text: str) -> tuple[str, RoutingDecision]:
    """Build routing decision: fast-path first, then LLM routing fallback.

    Returns (run_id, decision).
    """
    decision = try_fast_path(text)
    if decision is not None:
        run_id = f"direct-{decision.dag[0].id}" if decision.dag else "direct"
        logger.info("Fast-path: direct agent invocation: {}", [n.name for n in decision.dag])
        return run_id, decision

    # Fall through to full LLM routing
    kernel = Kernel()
    art = parse_text(text)
    run_id, decision = kernel.submit(art, persist=False)
    return run_id, decision


async def process_im_message(
    text: str,
    platform_name: str,
    *,
    target: str | None = None,
    user: str | None = None,
) -> BridgeResult:
    """Route an IM message through the test kernel and reply via platform.

    Supports direct agent invocation (@agent, "用 agent") and multi-turn
    conversation memory per user.

    Runs kernel.execute_sync in a thread to avoid blocking the event loop.
    """
    if not text.strip():
        return BridgeResult(ok=False, reply="", error="empty message")

    # Build context from conversation history for multi-turn
    mem_key = _memory_key(platform_name, user, target)
    mem = _get_memory(mem_key)
    context = mem.build_context(text)
    mem.add("user", text)

    loop = asyncio.get_running_loop()

    def _run() -> dict[str, Any]:
        run_id, decision = _build_decision(context)
        kernel = Kernel()
        return kernel.execute_sync(run_id, decision)

    try:
        summary = await asyncio.wait_for(
            loop.run_in_executor(None, _run),
            timeout=120,
        )
    except asyncio.TimeoutError:
        reply = "⏱️ Test-Agent timed out after 120s. Try a simpler request."
        mem.add("assistant", reply)
        await _send_reply(platform_name, reply, target)
        return BridgeResult(ok=False, reply=reply, error="timeout")
    except Exception as exc:
        logger.warning("IM bridge kernel failed: {}", exc)
        reply = f"❌ Test-Agent error: {exc}"
        mem.add("assistant", reply)
        await _send_reply(platform_name, reply, target)
        return BridgeResult(ok=False, reply=reply, error=str(exc))

    reply = _format_dag_summary(summary)
    mem.add("assistant", reply)

    try:
        await _send_reply(platform_name, reply, target)
    except Exception as exc:
        logger.warning("IM bridge send failed via {}: {}", platform_name, exc)
        return BridgeResult(ok=True, reply=reply, error=f"send failed: {exc}")

    return BridgeResult(ok=True, reply=reply)


async def _send_reply(platform_name: str, text: str, target: str | None) -> None:
    """Send a text reply through a gateway platform adapter."""
    platform = get_platform(platform_name)
    await platform.configure()
    msg = Message(text=text, user="test-agent")
    result = await platform.send(msg, target=target)
    if not result.ok:
        logger.warning("IM reply send failed via {}: {}", platform_name, result.error)
