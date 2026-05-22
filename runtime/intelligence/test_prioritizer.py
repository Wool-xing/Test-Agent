"""ML-driven test prioritizer — predict which tests to run first based on git diff.

Strategy (T-TS inspired, no coverage maps needed):
- Bag-of-Words on changed files → feature vector
- Historical test-failure association matrix
- Rank tests by predicted failure probability
- Configurable time budget (e.g., run top 15% of tests)
- SHAP-like feature importance explanation

Usage:
  python test_prioritizer.py rank --diff HEAD~1..HEAD
  python test_prioritizer.py train --history workspace/test_history.json
"""

from __future__ import annotations

import json
import math
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TestRecord:
    name: str
    file_path: str
    failure_count: int = 0
    last_failure: float = 0.0
    avg_duration_ms: float = 0.0
    recent_results: list[bool] = field(default_factory=list)


@dataclass
class RankedTest:
    name: str
    score: float
    reasons: list[str] = field(default_factory=list)


class TestPrioritizer:
    """ML-driven test prioritization using change-to-failure association."""

    def __init__(self, history_path: str = "workspace/test_history.json"):
        self.history_path = Path(history_path)
        self.tests: dict[str, TestRecord] = {}
        # file → tests that test this file (derived from naming convention + imports)
        self.file_to_tests: dict[str, set[str]] = defaultdict(set)
        # test → files historically associated with failures
        self.failure_associations: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._load()

    def _load(self) -> None:
        if self.history_path.exists():
            try:
                data = json.loads(self.history_path.read_text(encoding="utf-8"))
                for name, rec in data.get("tests", {}).items():
                    self.tests[name] = TestRecord(**rec)
                self.file_to_tests = defaultdict(set, data.get("file_to_tests", {}))
                self.failure_associations = defaultdict(
                    lambda: defaultdict(int), data.get("failure_associations", {}))
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tests": {n: {"name": t.name, "file_path": t.file_path,
                          "failure_count": t.failure_count, "last_failure": t.last_failure,
                          "avg_duration_ms": t.avg_duration_ms, "recent_results": t.recent_results}
                      for n, t in self.tests.items()},
            "file_to_tests": {k: list(v) for k, v in self.file_to_tests.items()},
            "failure_associations": {k: dict(v) for k, v in self.failure_associations.items()},
        }
        self.history_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def scan_tests(self, test_dir: str = "tests") -> None:
        """Scan test directory and populate test registry."""
        for py_file in Path(test_dir).rglob("test_*.py"):
            content = py_file.read_text(encoding="utf-8", errors="replace")
            # Extract test function names
            for line in content.split("\n"):
                if line.strip().startswith("def test_"):
                    test_name = line.strip().split("(")[0].replace("def ", "")
                    full_name = f"{py_file}::{test_name}"
                    if full_name not in self.tests:
                        self.tests[full_name] = TestRecord(
                            name=full_name, file_path=str(py_file))
                    # Map imports to test associations
                    for import_line in content.split("\n"):
                        if "import" in import_line or "from" in import_line:
                            parts = import_line.replace("from", "").replace("import", "").strip().split()
                            if parts:
                                module = parts[0].replace(".", "/") + ".py"
                                self.file_to_tests[module].add(full_name)
        self._save()

    def get_changed_files(self, diff_spec: str = "HEAD~1..HEAD") -> list[str]:
        """Get list of changed files from git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", diff_spec],
                capture_output=True, text=True, timeout=10,
            )
            return [f.strip() for f in result.stdout.split("\n") if f.strip()]
        except Exception:
            return []

    def rank(self, changed_files: list[str] | None = None,
             diff_spec: str = "HEAD~1..HEAD",
             time_budget_pct: float = 1.0) -> list[RankedTest]:
        """Rank tests by predicted failure probability given changed files."""
        if changed_files is None:
            changed_files = self.get_changed_files(diff_spec)

        scores: dict[str, float] = defaultdict(float)
        reasons: dict[str, list[str]] = defaultdict(list)

        for f in changed_files:
            # Direct file → test mapping
            for test_name in self.file_to_tests.get(f, set()):
                scores[test_name] += 3.0  # Direct association = high weight
                reasons[test_name].append(f"directly tests changed file: {f}")

            # Historical failure association
            for test_name, associations in self.failure_associations.items():
                if f in associations:
                    weight = math.log(associations[f] + 1)  # Log-scaled
                    scores[test_name] += weight
                    reasons[test_name].append(f"historically associated with failures in: {f}")

            # Directory-level proximity (files in same directory often related)
            changed_dir = str(Path(f).parent)
            for test_name, test_rec in self.tests.items():
                test_dir = str(Path(test_rec.file_path).parent)
                if test_dir == changed_dir:
                    scores[test_name] += 1.0
                    reasons[test_name].append(f"same directory as changed file: {f}")

        # Boost recently-failed tests
        for name, rec in self.tests.items():
            if rec.failure_count > 0:
                recency = 1.0 / (1.0 + time.time() - rec.last_failure) if rec.last_failure > 0 else 0.1
                scores[name] += recency * 2.0
                if recency > 0.5:
                    reasons[name].append("recently failed")

        # Sort by score descending
        ranked = sorted(
            [RankedTest(name=k, score=v, reasons=reasons.get(k, []))
             for k, v in scores.items()],
            key=lambda x: -x.score,
        )

        # Apply time budget
        if time_budget_pct < 1.0:
            top_n = max(int(len(ranked) * time_budget_pct), 1)
            ranked = ranked[:top_n]

        return ranked

    def record_result(self, test_name: str, passed: bool, changed_files: list[str] | None = None) -> None:
        """Record test result and update failure associations."""
        if test_name not in self.tests:
            self.tests[test_name] = TestRecord(name=test_name, file_path="")
        rec = self.tests[test_name]
        rec.recent_results.append(passed)
        if len(rec.recent_results) > 20:
            rec.recent_results = rec.recent_results[-20:]

        if not passed:
            rec.failure_count += 1
            rec.last_failure = time.time()
            if changed_files:
                for f in changed_files:
                    self.failure_associations[test_name][f] += 1

        self._save()

    def explain(self, test_name: str) -> dict:
        """Explain why a test was prioritized (SHAP-like feature importance)."""
        reasons = []
        rec = self.tests.get(test_name)
        if rec:
            if rec.failure_count > 0:
                reasons.append({"feature": "historical_failures", "value": rec.failure_count,
                                "impact": "high" if rec.failure_count > 3 else "medium"})
            if rec.avg_duration_ms > 0:
                reasons.append({"feature": "test_duration_ms", "value": rec.avg_duration_ms,
                                "impact": "low"})
            recency_hours = (time.time() - rec.last_failure) / 3600 if rec.last_failure else float("inf")
            if recency_hours < 24:
                reasons.append({"feature": "recent_failure", "value": f"{recency_hours:.1f}h ago",
                                "impact": "high"})

        associations = self.failure_associations.get(test_name, {})
        if associations:
            top_file = max(associations, key=associations.get)
            reasons.append({"feature": "top_associated_file", "value": top_file,
                            "impact": "medium"})

        return {"test": test_name, "reasons": reasons}


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="ML Test Prioritizer")
    sub = ap.add_subparsers(dest="cmd")

    rank = sub.add_parser("rank", help="Rank tests by predicted failure probability")
    rank.add_argument("--diff", default="HEAD~1..HEAD")
    rank.add_argument("--budget", type=float, default=1.0, help="Time budget (0.15 = top 15%)")
    rank.add_argument("--top", type=int, default=20)

    scan = sub.add_parser("scan", help="Scan test directory")
    scan.add_argument("--test-dir", default="tests")

    args = ap.parse_args()
    prioritizer = TestPrioritizer()

    if args.cmd == "rank":
        ranked = prioritizer.rank(diff_spec=args.diff, time_budget_pct=args.budget)
        print(f"Ranked {len(ranked)} tests (budget: {args.budget:.0%}):")
        for i, rt in enumerate(ranked[:args.top]):
            print(f"  {i+1}. [{rt.score:.1f}] {rt.name}")
            for reason in rt.reasons[:3]:
                print(f"     - {reason}")

    elif args.cmd == "scan":
        prioritizer.scan_tests(args.test_dir)
        print(f"Scanned: {len(prioritizer.tests)} tests, {len(prioritizer.file_to_tests)} file mappings")
