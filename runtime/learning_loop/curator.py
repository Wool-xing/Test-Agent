"""Curator coordinator.

Background skill maintenance:
  - inactivity-triggered (no daemon)
  - only touches agent-created skills
  - never auto-deletes — archives only
  - pinned skills bypass
  - uses aux client (runtime/subagent/aux_client)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from runtime.config.settings import get_settings


def _state_path() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning" / "curator"
    d.mkdir(parents=True, exist_ok=True)
    return d / "state.json"


def _archive_dir() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning" / "archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_state() -> dict:
    p = _state_path()
    if not p.is_file():
        return {"last_run_at": None, "paused": False, "runs_total": 0}
    return json.loads(p.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def is_due(*, interval_hours: int = 24) -> bool:
    state = _load_state()
    if state.get("paused"):
        return False
    last = state.get("last_run_at")
    if not last:
        return True
    delta = datetime.now(timezone.utc) - datetime.fromisoformat(last)
    return delta >= timedelta(hours=interval_hours)


def archive_skill(skill_path: Path, *, reason: str = "auto-archive") -> Path:
    """Move agent-created skill to archive/ (recoverable). Charter rule: NEVER delete."""
    if not skill_path.is_file():
        raise FileNotFoundError(skill_path)
    target = _archive_dir() / f"{skill_path.stem}__{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
    skill_path.rename(target)
    log = _archive_dir() / "archive.log"
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()}\t{skill_path}\t{target}\t{reason}\n")
    logger.info("archived skill {} -> {} (reason={})", skill_path, target, reason)
    return target


def restore_skill(archive_name: str, *, restore_dir: Path | None = None) -> Path:
    """Restore from archive. Counterpart to `archive_skill` (never auto-delete principle)."""
    src = _archive_dir() / archive_name
    if not src.is_file():
        raise FileNotFoundError(src)
    target_dir = restore_dir or (get_settings().resolve(get_settings().workspace_dir) / "learning" / "restored")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / archive_name
    src.rename(target)
    return target


def mark_run(outcome: str = "ok", details: dict[str, Any] | None = None) -> None:
    state = _load_state()
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["runs_total"] = state.get("runs_total", 0) + 1
    state.setdefault("history", []).append(
        {"ts": state["last_run_at"], "outcome": outcome, "details": details or {}}
    )
    state["history"] = state["history"][-50:]  # cap history
    _save_state(state)


def pause(paused: bool = True) -> None:
    state = _load_state()
    state["paused"] = paused
    _save_state(state)
