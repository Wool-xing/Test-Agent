"""mcp-compliance-checker MCP server.

Tools:
  - list_profiles(): list YAML files under profiles/compliance/
  - get_profile(name): return checks
  - check_compliance(profile, run_id?, evidence_keys?): match required evidence against run's actual evidence
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from runtime.config.settings import get_settings
from runtime.mcp.base import make_server, run_stdio, tool_decision_logged


def _profiles_dir() -> Path:
    s = get_settings()
    return s.resolve(Path("profiles/compliance"))


@tool_decision_logged("list_profiles")
async def tool_list_profiles() -> dict:
    d = _profiles_dir()
    files = sorted(p.stem for p in d.glob("*.yaml"))
    return {"profiles_dir": str(d), "count": len(files), "profiles": files}


def _load_profile(name: str) -> dict | None:
    # Charter security: 防 path traversal — 仅允许字母数字+连字符,且 resolve 后必须落在 profiles_dir 下
    import re

    if not re.fullmatch(r"[A-Za-z0-9_\-\.]+", name) or ".." in name:
        logger.warning("rejected profile name (illegal chars): {}", name)
        return None
    base = _profiles_dir().resolve()
    p = (base / f"{name}.yaml").resolve()
    try:
        p.relative_to(base)
    except ValueError:
        logger.warning("rejected profile path (escapes base): {}", p)
        return None
    if not p.is_file():
        return None
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@tool_decision_logged("get_profile")
async def tool_get_profile(name: str) -> dict:
    prof = _load_profile(name)
    if prof is None:
        return {"error": f"profile not found: {name}"}
    return prof


@tool_decision_logged("check_compliance")
async def tool_check_compliance(profile: str, run_id: str | None = None, evidence_keys: list[str] | None = None) -> dict:
    prof = _load_profile(profile)
    if prof is None:
        return {"error": f"profile not found: {profile}"}

    actual: set[str] = set(evidence_keys or [])
    if run_id and not actual:
        try:
            from runtime.storage.db import session_scope
            from runtime.storage.models import Evidence

            with session_scope() as s:
                rows = s.query(Evidence).filter(Evidence.run_id == run_id).all()
                actual = {r.minio_key for r in rows} | {r.kind.value for r in rows}
        except Exception as e:
            logger.warning("evidence fetch failed: {}", e)

    results = []
    pass_count = 0
    for check in prof.get("checks", []):
        required = set(check.get("evidence_required", []))
        missing = sorted(required - actual)
        status = "PASS" if not missing else "FAIL"
        if status == "PASS":
            pass_count += 1
        results.append(
            {
                "id": check.get("id"),
                "title": check.get("title"),
                "severity": check.get("severity"),
                "required_evidence": sorted(required),
                "missing_evidence": missing,
                "status": status,
            }
        )
    return {
        "profile": profile,
        "framework": prof.get("framework"),
        "version": prof.get("version"),
        "total_checks": len(results),
        "passed": pass_count,
        "failed": len(results) - pass_count,
        "pass_rate": pass_count / max(len(results), 1),
        "checks": results,
        "run_id": run_id,
        "skeleton_warning": prof.get("status") == "skeleton",
    }


def build_server():
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("compliance-checker")

    TOOLS = [
        Tool(
            name="list_profiles",
            description="List available compliance profiles under profiles/compliance/.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="get_profile",
            description="Get full compliance profile (checks + references).",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="check_compliance",
            description="Match a profile's evidence_required against a run's actual evidence. L4 被测项必触发(charter ).",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "run_id": {"type": "string"},
                    "evidence_keys": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["profile"],
                "additionalProperties": False,
            },
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {
        "list_profiles": tool_list_profiles,
        "get_profile": tool_get_profile,
        "check_compliance": tool_check_compliance,
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
