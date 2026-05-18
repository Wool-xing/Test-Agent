"""WebSocket streaming for real-time test run progress.

GET /run/{run_id}/stream — WebSocket endpoint that pushes node-by-node progress.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter(tags=["runs"])


class RunStream:
    """Per-run message queue for WebSocket broadcast."""

    def __init__(self, run_id: str, ttl_seconds: int = 3600) -> None:
        self.run_id = run_id
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.created_at = time.time()
        self.ttl = ttl_seconds

    async def push(self, event: dict[str, Any]) -> None:
        event["timestamp"] = time.time()
        await self._queue.put(event)

    async def get(self, timeout: float = 30.0) -> dict[str, Any] | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    @property
    def expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


_streams: dict[str, RunStream] = {}


def get_or_create_stream(run_id: str) -> RunStream:
    return _streams.setdefault(run_id, RunStream(run_id))


def push_node_event(run_id: str, node_id: str, status: str, output: dict | None = None) -> None:
    """Push a node execution event to the stream. Non-blocking fire-and-forget."""
    stream = _streams.get(run_id)
    if stream is None:
        return
    try:
        asyncio.ensure_future(stream.push({
            "type": "node_update",
            "node_id": node_id,
            "status": status,  # pending | running | done | failed | skipped
            "output": output,
        }))
    except RuntimeError:
        pass  # No running event loop — stream not active


def push_run_complete(run_id: str, ok: bool, summary: dict | None = None) -> None:
    """Push run completion event."""
    stream = _streams.get(run_id)
    if stream is None:
        return
    try:
        asyncio.ensure_future(stream.push({
            "type": "run_complete",
            "ok": ok,
            "summary": summary,
        }))
    except RuntimeError:
        pass


def cleanup_stream(run_id: str) -> None:
    _streams.pop(run_id, None)


@router.websocket("/run/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: str):
    await websocket.accept()
    stream = get_or_create_stream(run_id)
    logger.info("WebSocket stream connected for run {}", run_id)

    try:
        # Send existing progress
        await websocket.send_json({"type": "connected", "run_id": run_id})

        while True:
            event = await stream.get(timeout=30.0)
            if event is not None:
                await websocket.send_json(event)
            else:
                # Heartbeat ping
                await websocket.send_json({"type": "heartbeat", "run_id": run_id})

            # Check if client disconnected
            try:
                _ = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket stream disconnected for run {}", run_id)
    except Exception:
        logger.exception("WebSocket stream error for run {}", run_id)
    finally:
        cleanup_stream(run_id)
