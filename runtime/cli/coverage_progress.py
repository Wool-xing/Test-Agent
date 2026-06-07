"""Test coverage progress tracker — matrix of test types × modules.

Tracks which test categories have been executed against which project modules.
Persists to workspace/gateway/coverage_progress.json.
Visualizes as a Rich table with heatmap coloring.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

TEST_TYPES = ["unit", "integration", "e2e", "security", "performance", "visual", "api", "accessibility"]

DEFAULT_MODULES = ["auth", "api", "database", "frontend", "cli", "config", "reporting"]


@dataclass
class CoverageEntry:
    module: str
    test_type: str
    last_run: float = 0.0
    run_count: int = 0
    pass_count: int = 0
    notes: str = ""


def _file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "coverage_progress.json"


def _load() -> dict[str, list[CoverageEntry]]:
    p = _file()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        result: dict[str, list[CoverageEntry]] = {}
        for module, entries in data.items():
            result[module] = [CoverageEntry(**e) for e in entries]
        return result
    except (json.JSONDecodeError, TypeError):
        return {}


def _save(data: dict[str, list[CoverageEntry]]) -> None:
    out = {m: [asdict(e) for e in entries] for m, entries in data.items()}
    _file().write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def record_coverage(module: str, test_type: str, passed: bool, notes: str = "") -> None:
    """Record a test execution for a module."""
    if test_type not in TEST_TYPES:
        return
    data = _load()
    if module not in data:
        data[module] = []
    # Find or create entry
    for e in data[module]:
        if e.test_type == test_type:
            e.last_run = time.time()
            e.run_count += 1
            if passed:
                e.pass_count += 1
            if notes:
                e.notes = notes
            _save(data)
            return
    # New entry
    e = CoverageEntry(
        module=module, test_type=test_type,
        last_run=time.time(), run_count=1,
        pass_count=1 if passed else 0, notes=notes,
    )
    data[module].append(e)
    _save(data)


def get_matrix() -> tuple[list[str], list[str], dict[tuple[str, str], CoverageEntry]]:
    """Return (modules, test_types, matrix_dict)."""
    data = _load()
    modules = sorted(data.keys()) or DEFAULT_MODULES
    types = TEST_TYPES
    matrix: dict[tuple[str, str], CoverageEntry] = {}
    for m, entries in data.items():
        for e in entries:
            matrix[(m, e.test_type)] = e
    return modules, types, matrix


def get_summary() -> dict:
    """Return progress summary."""
    data = _load()
    total_slots = len(set(m for m in data)) * len(TEST_TYPES) if data else 0
    covered = 0
    recent_runs = 0
    for entries in data.values():
        for e in entries:
            if e.run_count > 0:
                covered += 1
                if time.time() - e.last_run < 86400:
                    recent_runs += 1
    return {
        "modules": len(data),
        "covered_slots": covered,
        "total_slots": total_slots or len(DEFAULT_MODULES) * len(TEST_TYPES),
        "recent_runs_24h": recent_runs,
        "coverage_pct": round(covered / max(total_slots, 1) * 100, 1),
    }
