"""Release readiness scoring — weighted multi‑dimension Go/No‑Go.

Standalone module. Called by dashboard / CLI / future test-lead integration.
Does NOT modify test_lead.py — usable independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ReadinessScore:
    verdict: str       # "GREEN" | "YELLOW" | "RED"
    score: float        # 0.0 – 1.0 weighted total
    breakdown: dict[str, float]  # per‑dimension contributions
    reason: str         # human‑readable explanation
    recommendation: str  # suggested action


def score_readiness(
    smoke_pass_rate: float = 0.0,
    regression_pass_rate: float = 0.0,
    perf_gate_ok: bool = False,
    security_ok: bool = False,
    p0_bug_count: int = 0,
) -> ReadinessScore:
    """Weighted multi‑dimension release readiness.

    Weights: smoke ×0.4 + regression ×0.3 + perf ×0.2 + security ×0.1

    Thresholds:
      - GREEN:  score ≥ 0.85 AND P0 bugs = 0
      - YELLOW: score ≥ 0.60 OR P0 bugs > 0 but score ≥ 0.6
      - RED:    score < 0.60 OR P0 bugs > 0 with score < 0.6
    """
    smoke_score = min(smoke_pass_rate, 1.0) * 0.4
    regression_score = min(regression_pass_rate, 1.0) * 0.3
    perf_score = (1.0 if perf_gate_ok else 0.0) * 0.2
    security_score = (1.0 if security_ok else 0.0) * 0.1

    total = smoke_score + regression_score + perf_score + security_score
    total = round(total, 3)

    breakdown = {
        "smoke": round(smoke_score, 3),
        "regression": round(regression_score, 3),
        "performance": round(perf_score, 3),
        "security": round(security_score, 3),
    }

    # Determine verdict
    if p0_bug_count > 0:
        if total >= 0.6:
            verdict = "YELLOW"
            reason = f"Score {total:.2f} ≥ 0.6 but {p0_bug_count} P0 bug(s) open"
            recommendation = f"Fix {p0_bug_count} P0 bug(s) before release"
        else:
            verdict = "RED"
            reason = f"Score {total:.2f} < 0.6 with {p0_bug_count} P0 bug(s)"
            recommendation = "Resolve P0 bugs and improve pass rates before considering release"
    elif total >= 0.85:
        verdict = "GREEN"
        reason = f"All gates passed (score {total:.2f})"
        recommendation = "Ready for release — human signoff required"
    elif total >= 0.6:
        verdict = "YELLOW"
        reason = f"Score {total:.2f} ≥ 0.6, conditional release"
        recommendation = "Conditional release — review known risks, obtain stakeholder approval"
    else:
        verdict = "RED"
        reason = f"Score {total:.2f} < 0.6"
        recommendation = "Do not release — improve test coverage and fix failures first"

    return ReadinessScore(
        verdict=verdict,
        score=total,
        breakdown=breakdown,
        reason=reason,
        recommendation=recommendation,
    )


def score_from_run_summary(run_summary: dict[str, Any]) -> ReadinessScore:
    """Convenience: compute readiness from a run summary dict (e.g. from dashboard)."""
    total = run_summary.get("total", 0)
    succeeded = run_summary.get("succeeded", run_summary.get("passed", 0))
    smoke_rate = succeeded / max(total, 1)
    regression_rate = succeeded / max(total, 1)  # same data source in current impl
    perf_ok = run_summary.get("perf_gate", run_summary.get("performance_ok", False))
    sec_ok = run_summary.get("security_ok", run_summary.get("security_gate", False))
    p0 = run_summary.get("p0_bug_count", run_summary.get("p0_bugs", 0))

    return score_readiness(
        smoke_pass_rate=smoke_rate,
        regression_pass_rate=regression_rate,
        perf_gate_ok=bool(perf_ok),
        security_ok=bool(sec_ok),
        p0_bug_count=int(p0),
    )


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Release readiness score (weighted multi‑dimension)")
    p.add_argument("--smoke", type=float, default=1.0, help="smoke pass rate (0-1)")
    p.add_argument("--regression", type=float, default=1.0, help="regression pass rate (0-1)")
    p.add_argument("--perf-ok", action="store_true", help="performance gate passed")
    p.add_argument("--security-ok", action="store_true", help="security gate passed")
    p.add_argument("--p0-bugs", type=int, default=0, help="P0 bug count")
    p.add_argument("--from-summary", help="path to run summary JSON")
    args = p.parse_args()

    if args.from_summary:
        import json as _json
        data = _json.loads(Path(args.from_summary).read_text(encoding="utf-8"))
        result = score_from_run_summary(data)
    else:
        result = score_readiness(
            smoke_pass_rate=args.smoke,
            regression_pass_rate=args.regression,
            perf_gate_ok=args.perf_ok,
            security_ok=args.security_ok,
            p0_bug_count=args.p0_bugs,
        )

    print(f"Verdict:       {result.verdict}")
    print(f"Score:         {result.score:.3f}")
    print(f"Breakdown:     smoke={result.breakdown['smoke']:.2f} "
          f"regression={result.breakdown['regression']:.2f} "
          f"perf={result.breakdown['performance']:.2f} "
          f"security={result.breakdown['security']:.2f}")
    print(f"Reason:        {result.reason}")
    print(f"Recommend:     {result.recommendation}")


if __name__ == "__main__":
    _cli()
