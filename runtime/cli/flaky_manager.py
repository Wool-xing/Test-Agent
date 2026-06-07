"""Flaky test manager — detect, track, and quarantine unstable tests.

Tracks pass/fail history per test node across runs.
Flaky = alternates between pass/fail (inconsistent results).
Quarantine = mark consistently flaky tests to exclude from gate.

Data: workspace/测试报告/baselines/flaky_tracker.json
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

FLAKY_THRESHOLD = 0.3     # <30% pass rate = flaky
QUARANTINE_THRESHOLD = 3  # ≥3 runs with inconsistent results = quarantine


@dataclass
class FlakyEntry:
    node_name: str
    run_history: list[dict] = field(default_factory=list)  # [{run_id, ok, ts}]
    flaky_score: float = 0.0
    quarantined: bool = False
    first_seen: float = 0.0


def _file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "测试报告" / "baselines"
    d.mkdir(parents=True, exist_ok=True)
    return d / "flaky_tracker.json"


def _load() -> dict[str, dict]:
    p = _file()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(data: dict) -> None:
    _file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_run(node_results: dict[str, dict], run_id: str) -> None:
    """Record results from a DAG execution for flaky detection."""
    data = _load()
    now = time.time()

    for nid, result in node_results.items():
        name = result.get("name", nid)
        ok = result.get("ok", False)
        key = name  # use node name as key across runs

        if key not in data:
            data[key] = asdict(FlakyEntry(node_name=name, first_seen=now))

        entry = data[key]
        entry.setdefault("run_history", [])
        entry["run_history"].append({"run_id": run_id, "ok": ok, "ts": now})

        # Keep last 20 runs
        if len(entry["run_history"]) > 20:
            entry["run_history"] = entry["run_history"][-20:]

        # Compute flaky score
        history = entry["run_history"]
        if len(history) >= 3:
            passes = sum(1 for r in history if r["ok"])
            pass_rate = passes / len(history)
            # Check alternation pattern
            changes = sum(1 for i in range(1, len(history))
                         if history[i]["ok"] != history[i-1]["ok"])
            change_rate = changes / max(len(history) - 1, 1)
            # Flaky score = combination of mid-pass-rate and high-change-rate
            entry["flaky_score"] = round((1.0 - abs(pass_rate - 0.5) * 2) * change_rate, 2)

            # Quarantine if consistently flaky
            if entry["flaky_score"] >= FLAKY_THRESHOLD and changes >= QUARANTINE_THRESHOLD:
                entry["quarantined"] = True

    _save(data)


def get_flaky_list() -> list[FlakyEntry]:
    """Return all tracked flaky entries sorted by score."""
    data = _load()
    entries = [FlakyEntry(**v) for v in data.values()]
    return sorted(entries, key=lambda e: e.flaky_score, reverse=True)


def get_quarantined() -> list[str]:
    """Return node names that are quarantined."""
    return [e.node_name for e in get_flaky_list() if e.quarantined]


def clear_tracker() -> None:
    _save({})
