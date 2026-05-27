"""Canary Analysis Config Generator — Argo Rollouts AnalysisTemplate from SLO definitions.

Generates:
- Argo Rollouts AnalysisTemplate CRDs
- Prometheus metrics queries for canary vs baseline comparison
- Statistical test configuration (Mann-Whitney U, t-test)
- Progressive traffic weight steps (5% → 25% → 50% → 100%)
- Error budget burn rate monitoring integration

Usage:
  python canary_config.py generate --service my-svc --slo-latency-ms 500
  python canary_config.py generate --from-slo-file slo.yaml --output analysis-template.yaml
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SLO:
    name: str
    target_pct: float = 99.9       # e.g. 99.9%
    error_budget_pct: float = 0.1  # 100 - target
    latency_p95_ms: float = 500.0
    error_rate_max: float = 0.01   # 1%


@dataclass
class CanaryStep:
    weight: int          # % of traffic to canary
    duration: str        # e.g. "5m", "10m", "30m"
    pause_after: bool = False


@dataclass
class AnalysisTemplate:
    name: str
    metrics: list[dict] = field(default_factory=list)
    steps: list[CanaryStep] = field(default_factory=list)
    success_condition: str = "all"  # all metrics must pass
    failure_limit: int = 2

    def to_argo_crd(self) -> dict:
        """Render as Argo Rollouts AnalysisTemplate CRD."""
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "AnalysisTemplate",
            "metadata": {"name": self.name},
            "spec": {
                "metrics": self.metrics,
                "successCondition": self.success_condition,
                "failureLimit": self.failure_limit,
            },
        }

    def to_argo_rollout(self, service: str, image_stable: str,
                         image_canary: str) -> dict:
        """Render as Argo Rollouts Rollout resource."""
        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Rollout",
            "metadata": {"name": f"{service}-rollout"},
            "spec": {
                "replicas": 3,
                "strategy": {
                    "canary": {
                        "analysis": {
                            "templates": [{"templateName": self.name}],
                        },
                        "steps": [{"setWeight": s.weight, "pause": {"duration": s.duration}}
                                   for s in self.steps],
                    },
                },
                "selector": {"matchLabels": {"app": service}},
                "template": {
                    "metadata": {"labels": {"app": service}},
                    "spec": {
                        "containers": [{
                            "name": service, "image": image_stable,
                        }],
                    },
                },
            },
        }


def generate_from_slo(service: str, slo: SLO,
                       traffic_steps: list[int] | None = None) -> AnalysisTemplate:
    """Generate AnalysisTemplate from SLO definitions."""
    if traffic_steps is None:
        traffic_steps = [5, 25, 50, 100]

    template = AnalysisTemplate(
        name=f"{service}-canary-analysis",
        steps=[CanaryStep(weight=w, duration="5m", pause_after=(w < 100))
               for w in traffic_steps],
    )

    # Metric 1: Error rate
    template.metrics.append({
        "name": "error-rate",
        "interval": "1m",
        "successCondition": f"result < {slo.error_rate_max}",
        "count": 5,
        "provider": {
            "prometheus": {
                "address": "http://prometheus:9090",
                "query": f'''
                    sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[5m]))
                    /
                    sum(rate(http_requests_total{{service="{service}"}}[5m]))
                '''.strip(),
            },
        },
    })

    # Metric 2: P95 latency
    template.metrics.append({
        "name": "p95-latency",
        "interval": "2m",
        "successCondition": f"result < {slo.latency_p95_ms / 1000}",
        "count": 3,
        "provider": {
            "prometheus": {
                "address": "http://prometheus:9090",
                "query": f'''
                    histogram_quantile(0.95,
                      sum(rate(http_request_duration_seconds_bucket{{service="{service}"}}[5m])) by (le))
                '''.strip(),
            },
        },
    })

    # Metric 3: Mann-Whitney U for canary vs baseline (Kayenta-style)
    template.metrics.append({
        "name": "canary-vs-baseline-mw",
        "interval": "3m",
        "successCondition": "result.p_value > 0.05",
        "count": 3,
        "provider": {
            "web": {
                "url": f"http://canary-analyzer:8080/mann-whitney?service={service}",
                "jsonPath": "{$.p_value}",
            },
        },
    })

    return template


# ═══════════════════════════════════════════════════════════════
# Mann-Whitney U for canary analysis
# ═══════════════════════════════════════════════════════════════

def mann_whitney_canary(canary_metrics: list[float],
                         baseline_metrics: list[float],
                         p_threshold: float = 0.05) -> dict:
    """Compare canary vs baseline using Mann-Whitney U test."""
    n1, n2 = len(canary_metrics), len(baseline_metrics)
    if n1 < 3 or n2 < 3:
        return {"significant": False, "reason": "too few samples"}

    combined = [(v, 0) for v in canary_metrics] + [(v, 1) for v in baseline_metrics]
    combined.sort(key=lambda x: x[0])

    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    r1 = sum(ranks[k] for k in range(len(combined)) if combined[k][1] == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    u = min(u1, u2)

    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mu) / sigma if sigma > 0 else 0
    p = 2 * (1 - _norm_cdf(abs(z)))

    return {
        "canary_mean": round(sum(canary_metrics) / n1, 4),
        "baseline_mean": round(sum(baseline_metrics) / n2, 4),
        "u_statistic": round(u, 2),
        "z_score": round(z, 4),
        "p_value": round(p, 4),
        "significant": p < p_threshold,
        "recommendation": "rollback" if p < p_threshold else "promote",
        "canary_sample_size": n1,
        "baseline_sample_size": n2,
    }


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ═══════════════════════════════════════════════════════════════
# Error budget burn rate
# ═══════════════════════════════════════════════════════════════

def error_budget_burn_rate(error_budget_pct: float, error_rate: float,
                            time_window_hours: float = 1.0) -> dict:
    """Calculate error budget burn rate and remaining budget."""
    budget_monthly = error_budget_pct / 100.0
    burn_rate = (error_rate / budget_monthly) if budget_monthly > 0 else float("inf")

    budget_remaining_hours = (budget_monthly / max(error_rate, 0.0001)) * 24 * 30

    alert = False
    if burn_rate > 1.0:
        alert = True   # Burning faster than allocation
    if burn_rate > 10.0:
        alert = True   # Critical: 10x burn rate

    return {
        "error_budget_pct": error_budget_pct,
        "current_error_rate": round(error_rate, 4),
        "burn_rate": round(burn_rate, 2),
        "budget_remaining_approx_hours": round(budget_remaining_hours, 1),
        "alert": alert,
        "alert_level": "critical" if burn_rate > 10 else ("warning" if burn_rate > 1 else "ok"),
    }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Canary Analysis Config Generator")
    sub = ap.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate Argo Rollouts AnalysisTemplate")
    gen.add_argument("--service", required=True)
    gen.add_argument("--slo-latency-ms", type=float, default=500)
    gen.add_argument("--slo-error-rate", type=float, default=0.01)
    gen.add_argument("--output", default="")

    mw = sub.add_parser("mann-whitney", help="Run Mann-Whitney U test")
    mw.add_argument("--canary-metrics", required=True, help="JSON array")
    mw.add_argument("--baseline-metrics", required=True, help="JSON array")

    burn = sub.add_parser("burn-rate", help="Calculate error budget burn rate")
    burn.add_argument("--budget-pct", type=float, default=0.1)
    burn.add_argument("--error-rate", type=float, required=True)

    args = ap.parse_args()

    if args.cmd == "generate":
        slo = SLO(name=args.service, latency_p95_ms=args.slo_latency_ms,
                  error_rate_max=args.slo_error_rate)
        template = generate_from_slo(args.service, slo)
        crd = template.to_argo_crd()
        output = yaml.dump(crd, default_flow_style=False, allow_unicode=True)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
        print(output)

    elif args.cmd == "mann-whitney":
        canary = json.loads(args.canary_metrics)
        baseline = json.loads(args.baseline_metrics)
        result = mann_whitney_canary(canary, baseline)
        print(json.dumps(result, indent=2))

    elif args.cmd == "burn-rate":
        result = error_budget_burn_rate(args.budget_pct, args.error_rate)
        print(json.dumps(result, indent=2))
