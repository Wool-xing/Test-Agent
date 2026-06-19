"""Workspace management — switch between project contexts.

Workspaces persist to workspace/gateway/workspaces.json.
Each workspace: name, path, project_name, tags.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

from runtime.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Workspace:
    name: str
    path: str
    project_name: str = ""
    tags: list[str] = field(default_factory=list)


def _file() -> Path:
    d = get_settings().gateway_dir
    d.mkdir(parents=True, exist_ok=True)
    return d / "workspaces.json"


def _load() -> list[dict]:
    p = _file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(workspaces: list[dict]) -> None:
    _file().write_text(json.dumps(workspaces, ensure_ascii=False, indent=2), encoding="utf-8")


def list_workspaces() -> list[Workspace]:
    return [Workspace(**w) for w in _load()]


def add_workspace(name: str, path: str, project_name: str = "", tags: list[str] | None = None) -> Workspace:
    ws = Workspace(name=name, path=path, project_name=project_name, tags=tags or [])
    workspaces = _load()
    workspaces.append(asdict(ws))
    _save(workspaces)
    return ws


def remove_workspace(name: str) -> bool:
    workspaces = _load()
    for i, w in enumerate(workspaces):
        if w.get("name") == name:
            workspaces.pop(i)
            _save(workspaces)
            return True
    return False


def switch_to(name: str) -> Workspace | None:
    """Switch CWD to workspace path. Returns workspace or None."""
    workspaces = _load()
    for w in workspaces:
        if w.get("name") == name:
            target = Path(w["path"])
            if target.is_dir():
                os.chdir(str(target))
                os.environ["PROJECT_NAME"] = w.get("project_name", name)
                logger.info("switched workspace: {} -> {}", name, target)
                return Workspace(**w)
    return None


def get_current() -> Workspace | None:
    """Get workspace matching current cwd."""
    cwd = str(get_settings().project_root)
    for w in _load():
        if w.get("path") == cwd:
            return Workspace(**w)
    return None


def auto_discover() -> Workspace | None:
    """Auto-discover current directory and add as workspace if not already registered."""
    cwd = get_settings().project_root
    existing = [w["path"] for w in _load()]
    if str(cwd) in existing:
        return None
    name = cwd.name
    is_git = (cwd / ".git").is_dir()
    proj_name = os.environ.get("PROJECT_NAME", name)
    ws = add_workspace(
        name=name, path=str(cwd),
        project_name=proj_name,
        tags=["git"] if is_git else [],
    )
    return ws
