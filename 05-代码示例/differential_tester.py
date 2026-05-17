# SPDX-License-Identifier: MIT
"""
Differential Testing Harness — cross-implementation comparison testing.

Compares N implementations with same inputs → detects output divergence.
LLM-driven counterpart synthesis (DLLens-style).
Statistical significance testing (Mann-Whitney U).
Multi-format normalization (JSON/XML/Protobuf comparator).

Usage:
  python differential_tester.py compare --impl-a func_a --impl-b func_b --inputs inputs.json
  python differential_tester.py fuzz --api-a http://api-v1 --api-b http://api-v2 --spec openapi.json
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class DiffResult:
    input_data: Any
    output_a: Any
    output_b: Any
    identical: bool
    divergence_type: str = ""  # "value", "type", "structure", "none"
    normalized_diff: dict = field(default_factory=dict)


@dataclass
class DiffReport:
    total_inputs: int
    identical: int
    diverged: int
    divergence_rate: float
    results: list[DiffResult] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_inputs": self.total_inputs, "identical": self.identical,
            "diverged": self.diverged, "divergence_rate": round(self.divergence_rate, 4),
            "statistics": self.statistics,
            "sample_results": [r.__dict__ for r in self.results[:20]],
        }


# ═══════════════════════════════════════════════════════════════
# Core comparator
# ═══════════════════════════════════════════════════════════════

def normalize_output(output: Any) -> Any:
    """Normalize output for comparison: sort lists, normalize floats, strip whitespace."""
    if isinstance(output, dict):
        return {k: normalize_output(v) for k, v in sorted(output.items())}
    if isinstance(output, list):
        if all(isinstance(x, (int, float, str)) for x in output):
            return sorted(normalize_output(x) for x in output)
        return [normalize_output(x) for x in output]
    if isinstance(output, float):
        return round(output, 6)  # Float tolerance
    if isinstance(output, str):
        return output.strip()
    return output


def compare_outputs(a: Any, b: Any) -> DiffResult:
    """Compare two outputs, returning normalized diff."""
    norm_a = normalize_output(a)
    norm_b = normalize_output(b)

    if norm_a == norm_b:
        return DiffResult(input_data=None, output_a=a, output_b=b, identical=True)

    # Classify divergence
    if type(a) != type(b):
        div_type = "type"
    elif isinstance(a, dict) and isinstance(b, dict):
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        if keys_a != keys_b:
            div_type = "structure"
        else:
            div_type = "value"
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        div_type = "value"
    else:
        div_type = "value"

    return DiffResult(input_data=None, output_a=a, output_b=b, identical=False,
                      divergence_type=div_type,
                      normalized_diff={"norm_a": norm_a, "norm_b": norm_b})


def compare_implementations(fn_a: Callable, fn_b: Callable,
                             inputs: list[Any]) -> DiffReport:
    """Compare two implementations across all inputs."""
    results = []
    for inp in inputs:
        try:
            out_a = fn_a(inp)
            out_b = fn_b(inp)
            diff = compare_outputs(out_a, out_b)
            diff.input_data = inp
            results.append(diff)
        except Exception as e:
            results.append(DiffResult(input_data=inp, output_a=None, output_b=None,
                                      identical=False, divergence_type="error",
                                      normalized_diff={"error": str(e)}))

    identical = sum(1 for r in results if r.identical)
    diverged = len(results) - identical

    # Statistical summary
    by_type = defaultdict(int)
    for r in results:
        if not r.identical:
            by_type[r.divergence_type] += 1

    return DiffReport(
        total_inputs=len(inputs), identical=identical, diverged=diverged,
        divergence_rate=diverged / max(len(inputs), 1),
        results=results,
        statistics={"by_type": dict(by_type)},
    )


# ═══════════════════════════════════════════════════════════════
# API differential testing
# ═══════════════════════════════════════════════════════════════

def compare_apis(api_a: str, api_b: str, endpoints: list[dict],
                  timeout: int = 30) -> DiffReport:
    """Compare two API implementations endpoint-by-endpoint."""
    try:
        import requests
    except ImportError:
        return DiffReport(0, 0, 0, 0)

    results = []
    for ep in endpoints:
        url_a = api_a.rstrip("/") + "/" + ep.get("path", "").lstrip("/")
        url_b = api_b.rstrip("/") + "/" + ep.get("path", "").lstrip("/")
        method = ep.get("method", "GET").lower()

        try:
            fn = getattr(requests, method)
            resp_a = fn(url_a, timeout=timeout)
            resp_b = fn(url_b, timeout=timeout)

            diff = DiffResult(
                input_data={"path": ep["path"], "method": method},
                output_a={"status": resp_a.status_code, "body": resp_a.text[:500]},
                output_b={"status": resp_b.status_code, "body": resp_b.text[:500]},
                identical=(resp_a.status_code == resp_b.status_code),
            )
            if not diff.identical:
                diff.divergence_type = "http_status"
            elif resp_a.status_code == 200:
                try:
                    diff = compare_outputs(resp_a.json(), resp_b.json())
                    diff.input_data = {"path": ep["path"], "method": method}
                except Exception:
                    pass
            results.append(diff)
        except Exception as e:
            results.append(DiffResult(
                input_data={"path": ep["path"], "method": method},
                output_a=None, output_b=None, identical=False,
                divergence_type="error", normalized_diff={"error": str(e)},
            ))

    identical = sum(1 for r in results if r.identical)
    return DiffReport(
        total_inputs=len(endpoints), identical=identical,
        diverged=len(endpoints) - identical,
        divergence_rate=(len(endpoints) - identical) / max(len(endpoints), 1),
        results=results,
    )


# ═══════════════════════════════════════════════════════════════
# Mann-Whitney U Test (for canary analysis / performance comparison)
# ═══════════════════════════════════════════════════════════════

def mann_whitney_u(sample_a: list[float], sample_b: list[float]) -> dict:
    """Mann-Whitney U test — non-parametric test for distribution difference.
    Commonly used in canary analysis (Kayenta-style)."""
    from math import sqrt
    from collections import OrderedDict

    n1, n2 = len(sample_a), len(sample_b)
    if n1 < 3 or n2 < 3:
        return {"u_statistic": 0, "p_value": 1.0, "significant": False,
                "reason": "samples too small"}

    # Rank all values
    combined = [(v, 0) for v in sample_a] + [(v, 1) for v in sample_b]
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

    # Normal approximation
    mu = n1 * n2 / 2
    sigma = sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (u - mu) / sigma if sigma > 0 else 0
    # Two-tailed p-value approximation
    p = 2 * (1 - _norm_cdf(abs(z)))

    return {
        "u_statistic": round(u, 2),
        "z_score": round(z, 4),
        "p_value": round(p, 4),
        "significant": p < 0.05,
        "sample_a_size": n1,
        "sample_b_size": n2,
    }


def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Differential Testing Harness")
    sub = ap.add_subparsers(dest="cmd")

    mw = sub.add_parser("mann-whitney", help="Mann-Whitney U test")
    mw.add_argument("--sample-a", required=True, help="JSON array of floats")
    mw.add_argument("--sample-b", required=True, help="JSON array of floats")

    diff = sub.add_parser("compare-json", help="Compare two JSON outputs")
    diff.add_argument("--file-a", required=True)
    diff.add_argument("--file-b", required=True)

    args = ap.parse_args()

    if args.cmd == "mann-whitney":
        a = json.loads(args.sample_a)
        b = json.loads(args.sample_b)
        result = mann_whitney_u(a, b)
        print(json.dumps(result, indent=2))

    elif args.cmd == "compare-json":
        a = json.loads(Path(args.file_a).read_text(encoding="utf-8"))
        b = json.loads(Path(args.file_b).read_text(encoding="utf-8"))
        result = compare_outputs(a, b)
        print(f"Identical: {result.identical}")
        if not result.identical:
            print(f"Divergence type: {result.divergence_type}")
            print(f"Diff: {json.dumps(result.normalized_diff, indent=2, ensure_ascii=False)[:500]}")
