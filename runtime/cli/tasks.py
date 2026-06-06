"""Task management — structured task list with completion criteria.

Tasks persist in workspace/gateway/tasks.json.
Each task: id, title, description, criteria, status, created_at, done_at.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

TASK_STATUSES = ("pending", "in_progress", "done", "cancelled")


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    description: str = ""
    criteria: list[str] = field(default_factory=list)  # completion conditions
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    done_at: float | None = None


def _tasks_file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "tasks.json"


def _load() -> list[dict]:
    p = _tasks_file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(tasks: list[dict]) -> None:
    _tasks_file().write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def add_task(title: str, description: str = "", criteria: list[str] | None = None) -> Task:
    """Add a new task. Returns the created Task."""
    task = Task(
        title=title.strip(),
        description=description.strip(),
        criteria=criteria or [],
    )
    tasks = _load()
    tasks.append(asdict(task))
    _save(tasks)
    return task


def list_tasks(status: str | None = None) -> list[Task]:
    """List tasks, optionally filtered by status."""
    tasks = _load()
    result = []
    for t in tasks:
        task = Task(**{k: v for k, v in t.items() if k in Task.__dataclass_fields__})
        if status and task.status != status:
            continue
        result.append(task)
    return sorted(result, key=lambda t: t.created_at, reverse=True)


def update_task(task_id: str, *, status: str | None = None, title: str | None = None) -> Task | None:
    """Update task status or title. Returns updated Task or None."""
    tasks = _load()
    for t in tasks:
        if t.get("id") == task_id:
            if status:
                t["status"] = status
                if status == "done":
                    t["done_at"] = time.time()
            if title:
                t["title"] = title.strip()
            _save(tasks)
            return Task(**{k: v for k, v in t.items() if k in Task.__dataclass_fields__})
    return None


def delete_task(task_id: str) -> bool:
    """Delete a task. Returns True if found and deleted."""
    tasks = _load()
    for i, t in enumerate(tasks):
        if t.get("id") == task_id:
            tasks.pop(i)
            _save(tasks)
            return True
    return False


def stats() -> dict:
    """Return task statistics."""
    tasks = _load()
    counts = {"pending": 0, "in_progress": 0, "done": 0, "cancelled": 0}
    for t in tasks:
        s = t.get("status", "pending")
        if s in counts:
            counts[s] += 1
    return {"total": len(tasks), **counts}
