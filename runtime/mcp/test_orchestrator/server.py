"""mcp-test-orchestrator MCP server.

Tools:
  - catalog():         list 16 experts + 32 skills
  - plan(target):      run router only, return DAG decision
  - run(target):       router + orchestrator, return execution summary
  - status(run_id):    fetch in-memory run status
  - report(run_id):    fetch execution report
"""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from typing import Any

from loguru import logger

from runtime.api.deps import Kernel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.mcp.base import make_server, run_stdio, tool_decision_logged

_kernel: Kernel | None = None
# Bounded LRU cache for in-memory run results.
# Charter §21 横切预算: 防 server 长时跑无限增长.
# Production should rely on Postgres `runs` table; this is the fast path.
_MAX_RUN_RESULTS = 1024
_run_results: OrderedDict[str, dict] = None  # type: ignore[assignment]


def _results_dict():
    global _run_results
    if _run_results is None:
        _run_results = OrderedDict()
    return _run_results


def _store_result(run_id: str, summary: dict) -> None:
    d = _results_dict()
    d[run_id] = summary
    d.move_to_end(run_id)
    while len(d) > _MAX_RUN_RESULTS:
        d.popitem(last=False)


def _k() -> Kernel:
    global _kernel
    if _kernel is None:
        _kernel = Kernel()
    return _kernel


def _build_artifact(target: str):
    """
    Build TargetArtifact from target string (path / URL / free text).

    Path traversal guard (W3-1, 同 evidence_vault 模式):
    本地文件读取仅限 project_root 下;外部路径 (e.g. /etc/passwd, ~/.ssh/*)
    降级为 parse_text 处理(不读文件,只当字符串分析)。
    """
    from pathlib import Path

    from loguru import logger

    if target.startswith(("http://", "https://")):
        return parse_url(target)

    p = Path(target)
    if p.exists():
        try:
            from runtime.config.settings import get_settings

            s = get_settings()
            resolved = p.resolve()
            project_root = Path(s.project_root).resolve()
            try:
                resolved.relative_to(project_root)
                # 路径在 project_root 下 → 允许读文件
                return parse_path(resolved)
            except ValueError:
                # 路径在 project_root 外 → 拒读文件,降级 parse_text
                logger.warning(
                    "path traversal blocked: '{}' resolved to '{}' is outside project_root '{}';"
                    " treating as plain text",
                    target, resolved, project_root,
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("path guard failed for '{}', treating as text: {}", target, e)

    return parse_text(target)


@tool_decision_logged("catalog")
async def tool_catalog() -> dict:
    return _k().catalog()


@tool_decision_logged("plan")
async def tool_plan(target: str) -> dict:
    art = _build_artifact(target)
    decision = _k().decide(art)
    return decision.model_dump()


@tool_decision_logged("run")
async def tool_run(target: str, persist: bool = False) -> dict:
    art = _build_artifact(target)
    run_id, decision = _k().submit(art, persist=persist)
    summary = _k().execute_sync(run_id, decision)
    _store_result(run_id, summary)
    return {"run_id": run_id, "summary": summary, "decision": decision.model_dump()}


@tool_decision_logged("status")
async def tool_status(run_id: str) -> dict:
    res = _results_dict().get(run_id)
    if res is None:
        return {"run_id": run_id, "status": "unknown_or_running"}
    return {
        "run_id": run_id,
        "status": "succeeded" if res.get("failed", 0) == 0 else "failed",
        "succeeded": res.get("succeeded", 0),
        "failed": res.get("failed", 0),
        "total": res.get("total", 0),
    }


@tool_decision_logged("report")
async def tool_report(run_id: str) -> dict:
    res = _results_dict().get(run_id)
    if res is None:
        return {"run_id": run_id, "error": "not_found"}
    return res


def build_server():
    """Construct MCP server with tools registered."""
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("test-orchestrator", version="0.1.0")

    TOOLS = [
        Tool(
            name="catalog",
            description="List 16 experts + 32 skills loaded from agents/* + skills/*.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="plan",
            description="Run AI router only; return DAG decision (no execution).",
            inputSchema={
                "type": "object",
                "properties": {"target": {"type": "string", "description": "file path | URL | free text"}},
                "required": ["target"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="run",
            description="Router + orchestrator end-to-end. Returns run_id + summary + decision.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "persist": {"type": "boolean", "default": False},
                },
                "required": ["target"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="status",
            description="Fetch in-memory status of a run_id.",
            inputSchema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="report",
            description="Fetch full execution report by run_id.",
            inputSchema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
                "additionalProperties": False,
            },
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {
        "catalog": tool_catalog,
        "plan": tool_plan,
        "run": tool_run,
        "status": tool_status,
        "report": tool_report,
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
