"""Cron job storage ().

Jobs persist in `workspace/cron/jobs.json`. Each entry:
  - id: uuid
  - cron: croniter expression
  - prompt: natural-language test request (will be routed)
  - enabled: bool
  - target_run: timestamp of next due
  - last_run: timestamp + outcome
  - max_runs: optional cap
  - delivery: list of gateway platforms (telegram/feishu/email/...)
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from runtime.config.settings import get_settings

try:
    from croniter import croniter

    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False
    croniter = None  # type: ignore

_lock = threading.Lock()


def _cron_dir() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "cron"
    d.mkdir(parents=True, exist_ok=True)
    (d / "output").mkdir(parents=True, exist_ok=True)
    return d


def _jobs_file() -> Path:
    return _cron_dir() / "jobs.json"


def _load() -> list[dict]:
    p = _jobs_file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error("jobs.json corrupt, treating as empty: {}", e)
        return []


def _save_atomic(jobs: list[dict]) -> None:
    p = _jobs_file()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def list_jobs() -> list[dict]:
    with _lock:
        return _load()


def add_job(
    cron_expr: str,
    prompt: str,
    *,
    enabled: bool = True,
    max_runs: int | None = None,
    delivery: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Create a new scheduled job. Returns job id."""
    if not HAS_CRONITER:
        raise RuntimeError("croniter not installed; pip install croniter")
    # validate expression
    croniter(cron_expr, datetime.now(timezone.utc))
    job_id = uuid.uuid4().hex[:16]
    next_at = croniter(cron_expr, datetime.now(timezone.utc)).get_next(datetime).isoformat()
    job = {
        "id": job_id,
        "cron": cron_expr,
        "prompt": prompt,
        "enabled": enabled,
        "next_at": next_at,
        "last_run": None,
        "max_runs": max_runs,
        "run_count": 0,
        "delivery": delivery or [],
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        jobs = _load()
        jobs.append(job)
        _save_atomic(jobs)
    logger.info("scheduled job {} cron={} prompt={!r}", job_id, cron_expr, prompt[:60])
    return job_id


def remove_job(job_id: str) -> bool:
    with _lock:
        jobs = _load()
        new = [j for j in jobs if j["id"] != job_id]
        if len(new) == len(jobs):
            return False
        _save_atomic(new)
        return True


def update_job(job_id: str, **changes) -> bool:
    with _lock:
        jobs = _load()
        for j in jobs:
            if j["id"] == job_id:
                j.update(changes)
                _save_atomic(jobs)
                return True
        return False


def due_jobs(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    return [j for j in list_jobs() if j.get("enabled") and j.get("next_at") and datetime.fromisoformat(j["next_at"]) <= now]


def advance_job(job_id: str, *, outcome: str = "ok", output_path: str | None = None) -> None:
    """Recompute next_at after a run, update run_count + last_run."""
    with _lock:
        jobs = _load()
        for j in jobs:
            if j["id"] != job_id:
                continue
            run_count = j.get("run_count", 0) + 1
            max_runs = j.get("max_runs")
            if max_runs and run_count >= max_runs:
                j["enabled"] = False
            j["run_count"] = run_count
            j["last_run"] = {"at": datetime.now(timezone.utc).isoformat(), "outcome": outcome, "output_path": output_path}
            try:
                j["next_at"] = croniter(j["cron"], datetime.now(timezone.utc)).get_next(datetime).isoformat()
            except Exception as e:
                logger.error("advance {}: croniter failed: {}", job_id, e)
                j["enabled"] = False
            _save_atomic(jobs)
            return


def output_dir(job_id: str) -> Path:
    d = _cron_dir() / "output" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d
