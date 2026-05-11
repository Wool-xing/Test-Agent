"""mcp-defect-tracker MCP server.

Tools wrap the 5 BugTrackerBase methods; delegate to existing
`utils/bug_manager.py` if available, else fall back to flywheel `defects` table.

Per charter §12 + §18-4: severity 1=P0 / 2=P1 / 3=P2 / 4=P3 一致。
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from typing import Any

from loguru import logger

from runtime.mcp.base import make_server, run_stdio, tool_decision_logged
from runtime.mcp.defect_tracker.base import ADAPTERS, BugRecord, get_adapter
from runtime.storage.db import session_scope
from runtime.storage.models import Defect, DefectSeverity, DefectStatus

SEVERITY_MAP = {1: DefectSeverity.p0, 2: DefectSeverity.p1, 3: DefectSeverity.p2, 4: DefectSeverity.p3}


def _flywheel_create(title: str, description: str, severity: int, **kwargs) -> str:
    sev = SEVERITY_MAP.get(severity, DefectSeverity.p2)
    with session_scope() as s:
        d = Defect(
            case_id=kwargs.get("case_id"),
            title=title,
            severity=sev,
            payload={"description": description, **kwargs},
        )
        s.add(d)
        s.flush()
        return str(d.id)


def _flywheel_get(bug_id: str) -> dict | None:
    try:
        bid = int(bug_id)
    except (TypeError, ValueError):
        return None
    with session_scope() as s:
        d = s.get(Defect, bid)
        if d is None:
            return None
        # Charter §18-4: 1=P0 / 2=P1 / 3=P2 / 4=P3 (one-based; enum value "P0".."P3" is zero-based string)
        sev_int = int(d.severity.value[1]) + 1 if d.severity.value.startswith("P") else 0
        return {
            "bug_id": str(d.id),
            "title": d.title,
            "severity": sev_int,
            "status": d.status.value,
            "url": d.external_url,
            "extra": d.payload,
        }


def _resolve_tracker() -> str:
    return os.getenv("BUG_TRACKER", "flywheel").lower()


@tool_decision_logged("create_bug")
async def tool_create_bug(
    title: str,
    description: str,
    severity: int = 2,
    *,
    tracker: str | None = None,
    case_id: int | None = None,
    reproduce_steps: str | None = None,
    attachments: list[str] | None = None,
) -> dict:
    tracker_name = tracker or _resolve_tracker()
    if tracker_name == "flywheel" or tracker_name not in ADAPTERS:
        bug_id = _flywheel_create(
            title, description, severity, case_id=case_id, reproduce_steps=reproduce_steps, attachments=attachments
        )
        return {"bug_id": bug_id, "tracker": "flywheel", "severity": f"P{severity-1}"}
    adapter = get_adapter(tracker_name)
    bug_id = adapter.submit_bug(
        title, description, severity, attachments=attachments, reproduce_steps=reproduce_steps
    )
    return {"bug_id": bug_id, "tracker": tracker_name, "severity": f"P{severity-1}"}


@tool_decision_logged("get_bug")
async def tool_get_bug(bug_id: str, *, tracker: str | None = None) -> dict:
    tracker_name = tracker or _resolve_tracker()
    if tracker_name == "flywheel" or tracker_name not in ADAPTERS:
        res = _flywheel_get(bug_id)
        return res or {"error": "not_found"}
    adapter = get_adapter(tracker_name)
    rec: BugRecord = adapter.get_status(bug_id)
    return asdict(rec)


@tool_decision_logged("update_bug")
async def tool_update_bug(bug_id: str, *, status: str | None = None, comment: str | None = None) -> dict:
    """Flywheel-only update (external trackers should use their own UI)."""
    try:
        bid = int(bug_id)
    except (TypeError, ValueError):
        return {"error": "bug_id not numeric (only flywheel updates supported in MVP)"}
    with session_scope() as s:
        d = s.get(Defect, bid)
        if d is None:
            return {"error": "not_found"}
        if status:
            d.status = DefectStatus(status)
        if comment:
            d.payload = (d.payload or {}) | {"comments": (d.payload or {}).get("comments", []) + [comment]}
        return {"bug_id": bug_id, "status": d.status.value}


@tool_decision_logged("query_bugs")
async def tool_query_bugs(
    *, severity: int | None = None, status: str | None = None, run_id: str | None = None, limit: int = 50
) -> dict:
    with session_scope() as s:
        q = s.query(Defect)
        if severity is not None:
            sev = SEVERITY_MAP.get(severity)
            if sev:
                q = q.filter(Defect.severity == sev)
        if status:
            q = q.filter(Defect.status == DefectStatus(status))
        rows = q.limit(limit).all()
        return {
            "count": len(rows),
            "items": [
                {
                    "bug_id": str(r.id),
                    "title": r.title,
                    "severity": r.severity.value,
                    "status": r.status.value,
                    "url": r.external_url,
                }
                for r in rows
            ],
        }


@tool_decision_logged("list_trackers")
async def tool_list_trackers() -> dict:
    return {
        "default": _resolve_tracker(),
        "registered_adapters": sorted(ADAPTERS.keys()),
        "flywheel_always_available": True,
    }


def build_server():
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("defect-tracker", version="0.1.0")

    TOOLS = [
        Tool(
            name="create_bug",
            description="Create a defect. severity 1=P0 / 2=P1 / 3=P2 / 4=P3 (charter §18-4).",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "integer", "enum": [1, 2, 3, 4]},
                    "tracker": {"type": "string", "description": "zentao/jira/github/linear/webhook/flywheel; omit = .env BUG_TRACKER"},
                    "case_id": {"type": "integer"},
                    "reproduce_steps": {"type": "string"},
                    "attachments": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "description"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_bug",
            description="Fetch a bug by id.",
            inputSchema={
                "type": "object",
                "properties": {"bug_id": {"type": "string"}, "tracker": {"type": "string"}},
                "required": ["bug_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="update_bug",
            description="Update status/comment (flywheel only).",
            inputSchema={
                "type": "object",
                "properties": {
                    "bug_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "resolved", "closed", "rejected"]},
                    "comment": {"type": "string"},
                },
                "required": ["bug_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="query_bugs",
            description="Filter bugs by severity/status/run_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {"type": "integer"},
                    "status": {"type": "string"},
                    "run_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="list_trackers",
            description="List configured trackers + default.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {
        "create_bug": tool_create_bug,
        "get_bug": tool_get_bug,
        "update_bug": tool_update_bug,
        "query_bugs": tool_query_bugs,
        "list_trackers": tool_list_trackers,
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
