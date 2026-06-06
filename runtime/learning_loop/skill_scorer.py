"""Skill scoring — auto-rate skills based on execution success, frequency, and speed.

Reads execution history from workspace output to compute quality scores per skill.
Surfaces underutilized skills and top performers for optimization recommendations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class SkillScore:
    name: str
    kind: str  # "expert" | "skill"
    runs: int = 0
    successes: int = 0
    failures: int = 0
    total_duration_ms: int = 0
    avg_duration_ms: int = 0
    success_rate: float = 0.0
    score: float = 0.0  # 0-100 composite
    last_seen: str = ""


def _workspace_output_dir() -> Path:
    """Find the workspace output directory with test results."""
    candidates = [
        Path("workspace/测试报告"),
        Path("workspace/_demo"),
    ]
    for p in candidates:
        resolved = Path(__file__).resolve().parents[2] / p
        if resolved.exists():
            return resolved
    return Path(__file__).resolve().parents[2] / "workspace"


def collect_execution_stats(limit: int = 200) -> list[dict]:
    """Scan workspace output files for execution records."""
    records: list[dict] = []
    base = _workspace_output_dir()
    if not base.exists():
        return records

    json_files = sorted(base.rglob("*.json"), reverse=True)
    for f in json_files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "results" in data:
                results = data["results"]
                if isinstance(results, dict):
                    for nid, r in results.items():
                        if isinstance(r, dict):
                            records.append({
                                "name": r.get("name", nid),
                                "kind": r.get("kind", "unknown"),
                                "ok": r.get("ok", False),
                                "duration_ms": r.get("duration_ms", 0),
                                "ts": data.get("timestamp", ""),
                            })
        except (json.JSONDecodeError, OSError):
            continue
    return records


def compute_scores(records: list[dict] | None = None) -> dict[str, SkillScore]:
    """Compute skill scores from execution records.

    Score formula: success_rate * 50 + min(30, freq * 5) + min(20, 1000 / max(avg_duration, 1))
    """
    if records is None:
        records = collect_execution_stats()

    stats: dict[str, dict] = {}
    for r in records:
        name = r["name"]
        if name not in stats:
            stats[name] = {
                "kind": r.get("kind", "unknown"),
                "runs": 0, "successes": 0, "failures": 0,
                "total_duration_ms": 0, "last_seen": r.get("ts", ""),
            }
        s = stats[name]
        s["runs"] += 1
        if r["ok"]:
            s["successes"] += 1
        else:
            s["failures"] += 1
        s["total_duration_ms"] += r.get("duration_ms", 0)
        if r.get("ts", "") > s["last_seen"]:
            s["last_seen"] = r["ts"]

    scores: dict[str, SkillScore] = {}
    for name, s in stats.items():
        runs = s["runs"]
        successes = s["successes"]
        rate = successes / runs if runs > 0 else 0.0
        avg_dur = s["total_duration_ms"] // runs if runs > 0 else 0

        # Composite score 0-100
        score = (
            rate * 50 +                                    # success weight
            min(30, runs * 5) +                            # frequency weight
            min(20, 1000 / max(avg_dur, 1))                # speed weight
        )

        scores[name] = SkillScore(
            name=name, kind=s["kind"],
            runs=runs, successes=successes, failures=s.get("failures", 0),
            total_duration_ms=s["total_duration_ms"],
            avg_duration_ms=avg_dur,
            success_rate=round(rate, 2),
            score=round(score, 1),
            last_seen=s["last_seen"],
        )

    return scores


def auto_learn_and_recommend() -> str | None:
    """Run after test execution: score skills + surface recommendations.

    Returns a recommendation string if interesting patterns found, else None.
    """
    records = collect_execution_stats(limit=100)
    if not records:
        return None

    scores = compute_scores(records)
    if not scores:
        return None

    parts: list[str] = []

    # Find underperformers (low success rate, enough runs)
    under = [(n, s) for n, s in scores.items() if s.runs >= 3 and s.success_rate < 0.5]
    if under:
        worst = sorted(under, key=lambda x: x[1].success_rate)[:3]
        parts.append("Underperforming: " + ", ".join(
            f"{n} ({s.success_rate:.0%})" for n, s in worst
        ))

    # Find unused but available skills (never run)
    try:
        from runtime.registry.registry import get_catalog
        cat = get_catalog()
        all_skills = set(cat.skills.keys())
        scored_names = set(scores.keys())
        unused = all_skills - scored_names
        if unused:
            sample = list(unused)[:5]
            parts.append("Unused: " + ", ".join(sample))
    except Exception:
        pass

    # Top performers
    top = sorted(scores.values(), key=lambda x: x.score, reverse=True)[:3]
    parts.append("Top: " + ", ".join(f"{s.name} ({s.score:.0f})" for s in top))

    return " | ".join(parts) if parts else None
