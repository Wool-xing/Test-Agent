"""Flywheel retrieval: similar past decisions as few-shot examples for routing.

M2-9: feeds top-k similar past inputs + their decided target_type as in-context.
Requires Postgres+pgvector + populated embeddings. Gracefully no-op otherwise.

Async-safety:
  - Called from sync `route()`. If already inside a running event loop (e.g. FastAPI
    request handler), running `asyncio.run` or `run_coroutine_threadsafe` on the
    same loop deadlocks. We detect that and degrade to no-op (charter §21 横切
    可复现性: never block, never silently misbehave).
"""

from __future__ import annotations

import asyncio
import json

from loguru import logger

from runtime.router.schema import TargetArtifact


def _artifact_text(artifact: TargetArtifact, limit: int = 2000) -> str:
    parts = []
    if artifact.text:
        parts.append(artifact.text[:limit])
    if artifact.path:
        parts.append(f"path={artifact.path}")
    if artifact.mime:
        parts.append(f"mime={artifact.mime}")
    if artifact.extra:
        parts.append(f"extra={json.dumps(artifact.extra, ensure_ascii=False)[:200]}")
    return "\n".join(parts).strip()


def _in_async_context() -> bool:
    try:
        asyncio.get_running_loop()
        return True
    except RuntimeError:
        return False


def build_similar_examples_block(artifact: TargetArtifact, top_k: int = 3) -> str:
    """Return a prompt prefix listing similar past cases. Empty string if unavailable.

    Safe to call from sync code only. In async context returns "" rather than
    risking deadlock; callers wanting retrieval inside async should await
    `build_similar_examples_block_async` directly.
    """
    if _in_async_context():
        logger.debug("retrieval skipped: caller is already in an async loop; use *_async variant")
        return ""
    try:
        return asyncio.run(build_similar_examples_block_async(artifact, top_k=top_k))
    except Exception as e:  # noqa: BLE001
        logger.debug("history retrieval skipped: {}", e)
        return ""


async def build_similar_examples_block_async(artifact: TargetArtifact, top_k: int = 3) -> str:
    """Async variant for use inside event loops (FastAPI handlers, etc.)."""
    try:
        from runtime.mcp.knowledge_base.server import tool_search_similar
    except ImportError as e:
        logger.debug("kb unavailable: {}", e)
        return ""
    text = _artifact_text(artifact)
    if not text:
        return ""
    try:
        result = await tool_search_similar(text=text, top_k=top_k, source_type="case")
    except Exception as e:  # noqa: BLE001
        logger.debug("retrieval error: {}", e)
        return ""
    if not isinstance(result, dict) or result.get("error") or not result.get("results"):
        return ""
    lines = ["# Similar past cases (flywheel retrieval, charter §M2-9):"]
    for r in result["results"]:
        lines.append(f"- similarity={r['similarity']:.2f} preview=\"{r['preview']}\"")
    lines.append("")
    lines.append("Use these as soft examples; do not blindly copy.")
    return "\n".join(lines)
