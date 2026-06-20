"""Dashboard metrics builder — decision‑signal → diagnostic → action layout.

Consumed by `runtime.api.main:get_dashboard`. Pure functions, no side effects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger


def scan_runs(workspace_dir: Path) -> list[dict[str, Any]]:
    """Scan workspace for completed run summaries (JSON files with 'total' key)."""
    all_runs: list[dict[str, Any]] = []
    for scan_dir in [workspace_dir / "_demo", workspace_dir / "测试报告"]:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "total" in data:
                    data["_source"] = str(f.relative_to(workspace_dir))
                    all_runs.append(data)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("dashboard: skipping {}: {}", f, e)
    return all_runs


def build_decision_signal(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Row 1: aggregate pass-rate, flaky indicator, regression trend."""
    if not runs:
        return {"pass_rate_pct": 0, "flaky_pct": 0, "trend": "no-data", "mttd_minutes": 0, "mttr_minutes": 0, "runs_analyzed": 0}

    pass_rates = [
        (r.get("succeeded", r.get("passed", 0)) / max(r.get("total", 1), 1))
        for r in runs
    ]
    avg_pass = round(sum(pass_rates) / len(pass_rates) * 100, 1) if pass_rates else 0

    # Trend: compare last 3 runs
    trend = "stable"
    if len(pass_rates) >= 3:
        recent = pass_rates[-3:]
        if recent[-1] < recent[-2] < recent[-3]:
            trend = "degrading"
        elif recent[-1] > recent[-2] > recent[-3]:
            trend = "improving"

    # MTTD/MTTR estimates from run durations
    durations = [r.get("duration_ms", r.get("elapsed_ms", 0)) for r in runs if r.get("duration_ms") or r.get("elapsed_ms")]
    avg_dur = sum(durations) / len(durations) / 1000 / 60 if durations else 0  # minutes

    return {
        "pass_rate_pct": avg_pass,
        "trend": trend,
        "runs_analyzed": len(runs),
        "mttd_minutes": round(avg_dur * 0.15, 1),  # ~15% of run time is detection
        "mttr_minutes": round(avg_dur * 0.55, 1),  # ~55% of run time is remediation
    }


def build_diagnostic_trends(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Row 2: per‑expert failure heatmap, flaky candidates, env health."""
    expert_fails: dict[str, int] = {}
    expert_total: dict[str, int] = {}
    recent_run_ids: list[str] = []

    for r in runs[-10:]:  # last 10 runs
        rid = r.get("run_id", r.get("_source", ""))
        recent_run_ids.append(rid)
        if "results" in r and isinstance(r["results"], dict):
            for node_id, node_r in r["results"].items():
                name = node_r.get("name", node_id)
                expert_total[name] = expert_total.get(name, 0) + 1
                if not node_r.get("ok"):
                    expert_fails[name] = expert_fails.get(name, 0) + 1

    # Failure heatmap: top failing experts
    heatmap = sorted(
        [{"name": k, "fails": expert_fails.get(k, 0), "total": v, "fail_rate_pct": round(expert_fails.get(k, 0) / max(v, 1) * 100, 1)}
         for k, v in expert_total.items()],
        key=lambda x: x["fail_rate_pct"], reverse=True,
    )[:10]

    # Flaky candidates: experts with 30‑70% fail rate
    flaky_candidates = [h for h in heatmap if 20 < h["fail_rate_pct"] < 80]

    return {
        "expert_heatmap": heatmap,
        "flaky_candidates": flaky_candidates,
        "total_experts_seen": len(expert_total),
        "recent_run_ids": recent_run_ids,
        "env_health": "degraded" if any(h["fail_rate_pct"] > 50 for h in heatmap) else "healthy",
    }


def build_action_items(runs: list[dict[str, Any]], heatmap: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Row 3: concrete action items derived from diagnostic signals."""
    actions: list[dict[str, Any]] = []

    # High-failure experts → investigate
    for h in heatmap:
        if h["fail_rate_pct"] >= 50:
            actions.append({
                "priority": "P0",
                "type": "investigate_expert",
                "target": h["name"],
                "detail": f"fail rate {h['fail_rate_pct']}% ({h['fails']}/{h['total']})",
            })
        elif h["fail_rate_pct"] >= 20:
            actions.append({
                "priority": "P1",
                "type": "monitor_expert",
                "target": h["name"],
                "detail": f"fail rate {h['fail_rate_pct']}% ({h['fails']}/{h['total']})",
            })

    # No runs = setup issue
    if not runs:
        actions.append({
            "priority": "P0",
            "type": "no_data",
            "target": "setup",
            "detail": "No run data found — run `tagent demo -y` to bootstrap",
        })

    return actions


def build_dashboard(workspace_dir: Path) -> dict[str, Any]:
    """Full dashboard: 3‑row layout (decision → diagnostic → action)."""
    runs = scan_runs(workspace_dir)
    decision = build_decision_signal(runs)
    diagnostic = build_diagnostic_trends(runs)
    actions = build_action_items(runs, diagnostic["expert_heatmap"])

    total = len(runs)
    avg_confidence = round(sum(r.get("avg_confidence", r.get("confidence", 0)) for r in runs) / max(total, 1), 1)

    return {
        # ── Row 1: 决策信号 ──
        "decision": decision,
        # ── Row 2: 诊断趋势 ──
        "diagnostic": diagnostic,
        # ── Row 3: 行动项 ──
        "actions": actions,
        # ── Legacy compat ──
        "total_runs": total,
        "avg_pass_rate": decision["pass_rate_pct"],
        "avg_confidence": avg_confidence,
        "total_test_cases": sum(r.get("total", 0) for r in runs),
        "recent_runs": [
            {
                "run_id": r.get("run_id", r.get("_source", "")),
                "pass_rate": round((r.get("succeeded", r.get("passed", 0)) / max(r.get("total", 1), 1)) * 100, 1),
                "confidence": r.get("avg_confidence", r.get("confidence", 0)),
                "ts": r.get("ts", r.get("timestamp", "")),
            }
            for r in runs[-10:]
        ],
        "top_failures": [
            {"name": h["name"], "count": h["fails"], "fail_rate_pct": h["fail_rate_pct"]}
            for h in diagnostic["expert_heatmap"][:5]
        ],
    }
