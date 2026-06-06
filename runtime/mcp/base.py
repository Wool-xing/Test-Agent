"""Shared MCP server scaffolding.

Honors charter:
  - §18-12 决策可追溯:工具调用自动落 `decisions/{date}_mcp_{tool}_{run_id}.json`
  - §21 横切可复现性:run_id 注入 + seed 记录 + 失败 snapshot
  - §1 同步铁律:服务列表必须与 `config/.mcp.json` 一致
"""

from __future__ import annotations

import functools
import json
import os
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path


def _get_project_version() -> str:
    """Read VERSION file, strip V prefix for semver compatibility."""
    try:
        vfile = Path(__file__).resolve().parent.parent.parent / "VERSION"
        if not vfile.exists():
            vfile = Path(os.getcwd()) / "VERSION"
        ver = vfile.read_text(encoding="utf-8").strip()
        return ver.lstrip("Vv")
    except (OSError, UnicodeDecodeError):
        return "0.1.0"
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from runtime.config.settings import get_settings


def new_run_id(prefix: str = "mcp") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _decisions_dir() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "测试报告" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_decision(tool: str, payload: dict, run_id: str | None = None) -> Path:
    """Persist a decision record per charter §18-12.

    Returns the written file path.
    """
    run_id = run_id or new_run_id()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"{ts}_mcp_{tool}_{run_id}.json"
    target = _decisions_dir() / fname
    record = {
        "ts": ts,
        "tool": tool,
        "run_id": run_id,
        "model_version": os.getenv("TAGENT_LLM_MODEL", "n/a"),
        "payload": payload,
    }
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def tool_decision_logged(tool_name: str) -> Callable:
    """Wrap an async MCP tool handler with decision logging.

    Charter §18-12 决策可追溯: every call (success or failure) writes a record.
    Logging failures must not mask the original handler exception/result.
    """

    def deco(fn: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            run_id = kwargs.pop("_run_id", None) or new_run_id(tool_name)
            log_args = list(args)
            log_kwargs = {k: v for k, v in kwargs.items()}
            log_kwargs["_run_id"] = run_id
            try:
                result = await fn(*args, **kwargs)
                try:
                    log_decision(tool_name, {"args": log_args, "kwargs": log_kwargs, "ok": True}, run_id)
                except Exception as log_err:  # noqa: BLE001
                    logger.warning("decision log failed for {}: {}", tool_name, log_err)
                return result
            except Exception as e:
                logger.exception("MCP tool {} failed", tool_name)
                try:
                    log_decision(
                        tool_name,
                        {"args": log_args, "kwargs": log_kwargs, "ok": False, "error": str(e)},
                        run_id,
                    )
                except Exception as log_err:  # noqa: BLE001
                    logger.warning("decision log failed for {}: {}", tool_name, log_err)
                raise

        return wrapper

    return deco


def make_server(name: str, version: str | None = None):
    if version is None:
        version = _get_project_version()
    """Return a low-level MCP Server instance."""
    try:
        from mcp.server import Server
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed; pip install mcp") from e
    return Server(name, version=version)


async def run_stdio(server) -> None:
    """Run an MCP server over stdio."""
    try:
        from mcp.server import NotificationOptions
        from mcp.server.models import InitializationOptions
        from mcp.server.stdio import stdio_server
    except ImportError as e:
        raise RuntimeError("mcp SDK missing components") from e
    async with stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name=server.name,
                server_version=_get_project_version(),
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
