"""Audit trail — structured, append‑only action log (JSONL).

Standalone module. Callers (API / CLI / orchestrator) opt in by calling log_event().
Does NOT modify existing code — integration is voluntary.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

_DEFAULT_DIR = Path("workspace/执行日志/audit")
_lock = threading.Lock()


def _audit_file() -> Path:
    _DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _DEFAULT_DIR / f"audit-{today}.jsonl"


def log_event(
    action: str,
    *,
    resource: str = "",
    resource_id: str = "",
    actor: str = "",
    details: dict[str, Any] | None = None,
    outcome: str = "success",
) -> None:
    """Append one audit event to today's JSONL file. Thread‑safe.

    Args:
        action: e.g. "run.start", "node.execute", "api.upload", "config.change"
        resource: e.g. "DAG", "testcase", "api_key"
        resource_id: e.g. run_id, node_id
        actor: who triggered (user / agent name / "system")
        details: arbitrary extra context
        outcome: "success" | "failure" | "skipped"
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "actor": actor or "system",
        "outcome": outcome,
        "details": details or {},
    }
    with _lock:
        try:
            with open(_audit_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("audit write failed: {}", e)


def query_events(
    action: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    actor: str | None = None,
    limit: int = 100,
    since_days: int = 7,
) -> list[dict[str, Any]]:
    """Read recent audit events matching optional filters."""
    results: list[dict[str, Any]] = []
    for d in sorted(_DEFAULT_DIR.glob("audit-*.jsonl"), reverse=True)[:since_days]:
        try:
            for line in d.read_text(encoding="utf-8").strip().split("\n"):
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if action and entry.get("action") != action:
                    continue
                if resource and entry.get("resource") != resource:
                    continue
                if resource_id and entry.get("resource_id") != resource_id:
                    continue
                if actor and entry.get("actor") != actor:
                    continue
                results.append(entry)
                if len(results) >= limit:
                    return results
        except OSError:
            continue
    return results


def audit_size() -> dict[str, Any]:
    """Return total audit entries + file count."""
    files = sorted(_DEFAULT_DIR.glob("audit-*.jsonl"))
    total = 0
    for f in files:
        try:
            total += len(f.read_text(encoding="utf-8").strip().split("\n"))
        except OSError:
            continue
    return {"files": len(files), "entries": total, "dir": str(_DEFAULT_DIR)}
