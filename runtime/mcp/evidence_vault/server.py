"""mcp-evidence-vault MCP server.

Tools:
  - upload_evidence(run_id, kind, content_b64, filename?): upload bytes to MinIO + index in Postgres
  - upload_evidence_path(run_id, kind, path): upload from local path
  - list_evidence(run_id): list evidence rows for a run
  - get_evidence(evidence_id): fetch bytes by id
  - search_evidence(filters): list by kind/run_id/sha256
"""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from loguru import logger

from runtime.mcp.base import make_server, run_stdio, tool_decision_logged
from runtime.storage.db import session_scope
from runtime.storage.models import Evidence, EvidenceKind
from runtime.storage.objects import ObjectStore
from runtime.storage.repo import add_evidence


def _store() -> ObjectStore:
    return ObjectStore()


def _persist_evidence(run_id: str, kind: str, data: bytes, key: str) -> dict:
    """DB insert first, then MinIO upload; if upload fails, rollback DB row.

    Charter §18 闭环约定: 防止 MinIO 与 Postgres 不一致 (orphaned file or dangling row).
    """
    import hashlib

    sha = hashlib.sha256(data).hexdigest()
    eid = add_evidence(run_id, EvidenceKind(kind), key, sha256=sha, size_bytes=len(data))
    try:
        _store().put_bytes(key, data)
    except Exception as e:
        # Rollback DB row to avoid dangling reference
        from runtime.storage.db import session_scope
        from runtime.storage.models import Evidence

        try:
            with session_scope() as s:
                row = s.get(Evidence, eid)
                if row is not None:
                    s.delete(row)
        except Exception as rb_err:
            logger.error("rollback evidence row {} failed: {}", eid, rb_err)
        raise RuntimeError(f"MinIO upload failed for {key}: {e}") from e
    return {"evidence_id": eid, "minio_key": key, "sha256": sha, "size_bytes": len(data)}


@tool_decision_logged("upload_evidence")
async def tool_upload_evidence(run_id: str, kind: str, content_b64: str, filename: str | None = None) -> dict:
    """Upload base64-encoded bytes."""
    data = base64.b64decode(content_b64)
    key = f"{run_id}/{filename or f'evidence-{len(data)}.bin'}"
    return _persist_evidence(run_id, kind, data, key)


@tool_decision_logged("upload_evidence_path")
async def tool_upload_evidence_path(run_id: str, kind: str, path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        return {"error": f"file not found: {path}"}
    data = p.read_bytes()
    key = f"{run_id}/{p.name}"
    return _persist_evidence(run_id, kind, data, key) | {"source_path": str(p)}


@tool_decision_logged("list_evidence")
async def tool_list_evidence(run_id: str) -> dict:
    with session_scope() as s:
        rows = s.query(Evidence).filter(Evidence.run_id == run_id).all()
        return {
            "run_id": run_id,
            "count": len(rows),
            "items": [
                {
                    "id": r.id,
                    "kind": r.kind.value,
                    "minio_key": r.minio_key,
                    "sha256": r.sha256,
                    "size_bytes": r.size_bytes,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        }


@tool_decision_logged("get_evidence")
async def tool_get_evidence(evidence_id: int) -> dict:
    with session_scope() as s:
        e = s.get(Evidence, evidence_id)
        if e is None:
            return {"error": "not_found"}
        data = _store().get_bytes(e.minio_key)
        return {
            "evidence_id": e.id,
            "kind": e.kind.value,
            "minio_key": e.minio_key,
            "sha256": e.sha256,
            "content_b64": base64.b64encode(data).decode("ascii"),
            "size_bytes": e.size_bytes,
        }


@tool_decision_logged("search_evidence")
async def tool_search_evidence(kind: str | None = None, sha256: str | None = None, run_id: str | None = None) -> dict:
    with session_scope() as s:
        q = s.query(Evidence)
        if kind:
            q = q.filter(Evidence.kind == EvidenceKind(kind))
        if sha256:
            q = q.filter(Evidence.sha256 == sha256)
        if run_id:
            q = q.filter(Evidence.run_id == run_id)
        rows = q.limit(100).all()
        return {
            "count": len(rows),
            "items": [
                {"id": r.id, "run_id": r.run_id, "kind": r.kind.value, "minio_key": r.minio_key, "sha256": r.sha256}
                for r in rows
            ],
        }


def build_server():
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("evidence-vault", version="0.1.0")

    TOOLS = [
        Tool(
            name="upload_evidence",
            description="Upload base64-encoded bytes as evidence. kind ∈ log/screenshot/video/har/report/other.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["log", "screenshot", "video", "har", "report", "other"]},
                    "content_b64": {"type": "string"},
                    "filename": {"type": "string"},
                },
                "required": ["run_id", "kind", "content_b64"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="upload_evidence_path",
            description="Upload evidence from a local file path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["log", "screenshot", "video", "har", "report", "other"]},
                    "path": {"type": "string"},
                },
                "required": ["run_id", "kind", "path"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="list_evidence",
            description="List evidence rows for a run_id.",
            inputSchema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_evidence",
            description="Fetch evidence bytes by id (returned as base64).",
            inputSchema={
                "type": "object",
                "properties": {"evidence_id": {"type": "integer"}},
                "required": ["evidence_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="search_evidence",
            description="Search evidence by kind / sha256 / run_id (any combination).",
            inputSchema={
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "sha256": {"type": "string"},
                    "run_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {
        "upload_evidence": tool_upload_evidence,
        "upload_evidence_path": tool_upload_evidence_path,
        "list_evidence": tool_list_evidence,
        "get_evidence": tool_get_evidence,
        "search_evidence": tool_search_evidence,
    }

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list:
        arguments = arguments or {}
        handler = DISPATCH.get(name)
        if handler is None:
            return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            logger.exception("tool {} failed", name)
            return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]

    return server


def main():
    server = build_server()
    asyncio.run(run_stdio(server))


if __name__ == "__main__":
    main()
