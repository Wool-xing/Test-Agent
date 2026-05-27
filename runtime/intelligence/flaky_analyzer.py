"""Flaky Root Cause Analyzer — Google Auto-Diagnose style LLM-powered diagnosis.

Key design (per Google ICSE 2026 paper):
- Collect ALL logs (test driver + SUT components, INFO+ level)
- Merge by timestamp into unified stream
- Structured prompt with explicit NEGATIVE CONSTRAINTS
  ("If logs don't contain evidence, DO NOT guess")
- Output: ==Conclusion== + ==Investigation Steps== + ==Most Relevant Log Lines==
"""

from __future__ import annotations

import contextlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LogEntry:
    timestamp: float
    source: str       # "test", "sut", "db", "network"
    level: str        # INFO, WARN, ERROR
    message: str


@dataclass
class DiagnosisResult:
    conclusion: str
    root_cause_category: str  # "test_logic", "environment", "dependency", "timing", "data", "unknown"
    investigation_steps: list[str] = field(default_factory=list)
    relevant_log_lines: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_human: bool = False


# ═══════════════════════════════════════════════════════════════
# Log Collection
# ═══════════════════════════════════════════════════════════════

def collect_logs(log_dir: str = "workspace/logs",
                  pattern: str = "*.log") -> list[LogEntry]:
    """Collect and merge logs from multiple sources."""
    entries = []
    log_path = Path(log_dir)
    if not log_path.exists():
        return entries

    for log_file in log_path.rglob(pattern):
        source = _infer_source(log_file.name)
        try:
            for line in log_file.read_text(encoding="utf-8", errors="replace").split("\n")[-500:]:
                entry = _parse_log_line(line, source)
                if entry:
                    entries.append(entry)
        except Exception:
            continue

    entries.sort(key=lambda e: e.timestamp)
    return entries


def _infer_source(filename: str) -> str:
    name = filename.lower()
    if "test" in name or "pytest" in name:
        return "test"
    if "db" in name or "postgres" in name or "mysql" in name:
        return "db"
    if "nginx" in name or "proxy" in name or "gateway" in name:
        return "network"
    return "sut"


def _parse_log_line(line: str, source: str) -> LogEntry | None:
    """Parse common log formats: ISO timestamp, log level."""
    if not line.strip():
        return None
    # Try ISO timestamp
    ts_match = re.match(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
    ts = time.time()
    if ts_match:
        with contextlib.suppress(ValueError):
            ts = time.mktime(time.strptime(ts_match.group(1)[:19], "%Y-%m-%dT%H:%M:%S"))

    level = "INFO"
    for lv in ["ERROR", "CRITICAL", "WARN", "WARNING", "INFO", "DEBUG"]:
        if lv in line:
            level = lv if lv != "WARNING" else "WARN"
            break

    return LogEntry(timestamp=ts, source=source, level=level, message=line[:500])


# ═══════════════════════════════════════════════════════════════
# LLM Diagnosis (heuristic fallback when no LLM available)
# ═══════════════════════════════════════════════════════════════

def diagnose_heuristic(test_name: str, logs: list[LogEntry],
                        failure_output: str = "") -> DiagnosisResult:
    """Heuristic root cause analysis (no LLM required).
    Production path should use diagnose_with_llm()."""

    errors = [e for e in logs if e.level in ("ERROR", "CRITICAL")]
    test_errors = [e for e in errors if e.source == "test"]
    sut_errors = [e for e in errors if e.source == "sut"]
    db_errors = [e for e in errors if e.source == "db"]
    network_errors = [e for e in errors if e.source == "network"]

    # Rule 1: Only test errors → test logic issue
    if test_errors and not sut_errors and not db_errors and not network_errors:
        return DiagnosisResult(
            conclusion=f"Test logic issue in {test_name}",
            root_cause_category="test_logic",
            investigation_steps=[
                "Review test assertions for correctness",
                "Check if test data setup is correct",
                "Verify mock/stub behavior matches real system",
            ],
            relevant_log_lines=[e.message[:200] for e in test_errors[:5]],
            confidence=0.7,
        )

    # Rule 2: DB errors → infrastructure
    if db_errors:
        return DiagnosisResult(
            conclusion=f"Database failure affecting {test_name}",
            root_cause_category="dependency",
            investigation_steps=[
                "Check database connection pool",
                "Verify database is running and accessible",
                "Check for deadlocks or lock contention",
            ],
            relevant_log_lines=[e.message[:200] for e in db_errors[:5]],
            confidence=0.8,
        )

    # Rule 3: Network errors → connectivity
    if network_errors:
        return DiagnosisResult(
            conclusion=f"Network connectivity failure in {test_name}",
            root_cause_category="environment",
            investigation_steps=[
                "Check network connectivity to external services",
                "Verify DNS resolution",
                "Check for firewall/iptables rules",
            ],
            relevant_log_lines=[e.message[:200] for e in network_errors[:5]],
            confidence=0.75,
        )

    # Rule 4: SUT errors → application bug
    if sut_errors:
        return DiagnosisResult(
            conclusion=f"Application error detected during {test_name}",
            root_cause_category="dependency",
            investigation_steps=[
                "Review SUT error logs for application bugs",
                "Check if SUT was recently deployed/changed",
                "Verify environment configuration",
            ],
            relevant_log_lines=[e.message[:200] for e in sut_errors[:5]],
            confidence=0.65,
        )

    # Rule 5: No errors found → timing/flaky
    return DiagnosisResult(
        conclusion=f"No clear error pattern found for {test_name} — likely timing or flaky test",
        root_cause_category="timing",
        investigation_steps=[
            "Re-run test in isolation to check for flakiness",
            "Check for race conditions or async timing issues",
            "Review test for hardcoded timeouts/sleeps",
        ],
        relevant_log_lines=failure_output.split("\n")[:5] if failure_output else [],
        confidence=0.3,
        needs_human=True,
    )


def diagnose_with_llm(test_name: str, logs: list[LogEntry],
                       failure_output: str = "",
                       max_tokens: int = 1000) -> DiagnosisResult:
    """LLM-powered diagnosis following Google Auto-Diagnose prompt pattern."""
    # Build unified log stream
    log_stream = "\n".join(
        f"[{e.source}:{e.level}] {e.message[:300]}"
        for e in logs[-100:]  # Last 100 entries
    )

    system_prompt = """You are a test failure root cause analyzer.
Your task: analyze test failure logs and determine root cause.

CRITICAL RULES:
1. If the logs do NOT contain clear evidence about the failure, say so. Do NOT guess.
2. Cite specific log lines as evidence.
3. Distinguish between: test logic bug, environment issue, dependency failure, timing/race condition, or data problem.
4. Be concise. Output in this format:

==Conclusion==
[One sentence root cause or "Insufficient evidence to determine root cause"]

==Root Cause Category==
[test_logic | environment | dependency | timing | data | unknown]

==Investigation Steps==
- [Step 1]
- [Step 2]

==Most Relevant Log Lines==
[Up to 5 most relevant log lines]

==Confidence==
[0.0 to 1.0]"""

    user_prompt = f"""Test: {test_name}

Failure output:
{failure_output[:500]}

Unified log stream (merged by timestamp):
{log_stream[:3000]}"""

    try:
        from runtime.subagent.aux_client import aux_client
        client = aux_client()
        raw = client.complete(system_prompt, user_prompt, temperature=0.1, max_tokens=max_tokens)
        return _parse_llm_response(raw, test_name)
    except Exception:
        return diagnose_heuristic(test_name, logs, failure_output)


def _parse_llm_response(raw: str, test_name: str) -> DiagnosisResult:
    """Parse structured LLM output."""
    conclusion = ""
    category = "unknown"
    steps = []
    log_lines = []
    confidence = 0.5

    concl_match = re.search(r'==Conclusion==\s*\n(.+)', raw)
    if concl_match:
        conclusion = concl_match.group(1).strip()

    cat_match = re.search(r'==Root Cause Category==\s*\n(.+)', raw)
    if cat_match:
        cat_raw = cat_match.group(1).strip().lower()
        for c in ["test_logic", "environment", "dependency", "timing", "data", "unknown"]:
            if c in cat_raw:
                category = c
                break

    steps_match = re.search(r'==Investigation Steps==\s*\n(.+?)(?=\n==|$)', raw, re.DOTALL)
    if steps_match:
        steps = [s.strip("- ") for s in steps_match.group(1).strip().split("\n") if s.strip()]

    logs_match = re.search(r'==Most Relevant Log Lines==\s*\n(.+?)(?=\n==|$)', raw, re.DOTALL)
    if logs_match:
        log_lines = [line.strip("- ") for line in logs_match.group(1).strip().split("\n") if line.strip()]

    conf_match = re.search(r'==Confidence==\s*\n([\d.]+)', raw)
    if conf_match:
        with contextlib.suppress(ValueError):
            confidence = float(conf_match.group(1))

    return DiagnosisResult(
        conclusion=conclusion or f"Analysis for {test_name}",
        root_cause_category=category,
        investigation_steps=steps,
        relevant_log_lines=log_lines,
        confidence=confidence,
        needs_human=confidence < 0.5,
    )


# ═══════════════════════════════════════════════════════════════
# Batch analyzer
# ═══════════════════════════════════════════════════════════════

def analyze_failures(test_failures: list[dict],
                      log_dir: str = "workspace/logs",
                      use_llm: bool = False) -> list[DiagnosisResult]:
    """Batch analyze multiple test failures."""
    logs = collect_logs(log_dir)
    results = []

    for failure in test_failures:
        test_name = failure.get("nodeid", failure.get("name", "unknown"))
        output = failure.get("output", failure.get("error", ""))

        if use_llm:
            result = diagnose_with_llm(test_name, logs, output)
        else:
            result = diagnose_heuristic(test_name, logs, output)

        results.append(result)

    # Summary: cluster by root cause
    by_category: dict[str, int] = {}
    for r in results:
        by_category[r.root_cause_category] = by_category.get(r.root_cause_category, 0) + 1

    return results


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Flaky Root Cause Analyzer")
    sub = ap.add_subparsers(dest="cmd")

    diag = sub.add_parser("diagnose", help="Diagnose a test failure")
    diag.add_argument("--test-name", required=True)
    diag.add_argument("--log-dir", default="workspace/logs")
    diag.add_argument("--failure-output", default="")
    diag.add_argument("--llm", action="store_true")

    batch = sub.add_parser("batch", help="Batch analyze failures from JSON")
    batch.add_argument("--failures-file", required=True)
    batch.add_argument("--log-dir", default="workspace/logs")
    batch.add_argument("--llm", action="store_true")

    args = ap.parse_args()

    if args.cmd == "diagnose":
        logs = collect_logs(args.log_dir)
        if args.llm:
            result = diagnose_with_llm(args.test_name, logs, args.failure_output)
        else:
            result = diagnose_heuristic(args.test_name, logs, args.failure_output)
        print(f"Root cause: {result.root_cause_category}")
        print(f"Conclusion: {result.conclusion}")
        print(f"Confidence: {result.confidence:.0%}")
        if result.investigation_steps:
            print("Steps:")
            for s in result.investigation_steps:
                print(f"  - {s}")

    elif args.cmd == "batch":
        failures = json.loads(Path(args.failures_file).read_text(encoding="utf-8"))
        if not isinstance(failures, list):
            failures = [failures]
        results = analyze_failures(failures, args.log_dir, args.llm)
        for r in results:
            print(f"[{r.root_cause_category}] {r.conclusion[:100]} ({r.confidence:.0%})")
