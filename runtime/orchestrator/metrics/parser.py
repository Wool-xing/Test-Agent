"""Parse junit XML and JMeter JTL into structured metrics for gate enforcement."""

from __future__ import annotations

import statistics
import xml.etree.ElementTree as ET
from typing import Any


def parse_junit(xml_text: str) -> dict[str, Any]:
    """Extract test counts and pass rate from junit XML.

    Returns: {total, passed, failed, errors, skipped, rate}
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}

    total = int(root.attrib.get("tests", 0))
    failures = int(root.attrib.get("failures", 0))
    errors = int(root.attrib.get("errors", 0))
    skipped = int(root.attrib.get("skipped", 0))
    failed = failures + errors
    passed = total - failed - skipped

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "rate": passed / total if total > 0 else 0.0,
    }


def parse_jmeter_jtl(csv_text: str) -> dict[str, Any]:
    """Extract sample counts, latency stats, and success rate from JMeter JTL.

    Returns: {samples, failures, avg_ms, p95_ms, min_ms, max_ms, rate}
    """
    lines = [l.strip() for l in csv_text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return {"samples": 0, "failures": 0, "avg_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0, "rate": 0.0}

    header = lines[0].split(",")
    data_lines = lines[1:]

    try:
        elapsed_idx = header.index("elapsed")
        success_idx = header.index("success")
    except ValueError:
        return {}

    elapsed_values = []
    failures = 0
    for line in data_lines:
        fields = line.split(",")
        if len(fields) <= max(elapsed_idx, success_idx):
            continue
        try:
            elapsed_values.append(int(fields[elapsed_idx]))
        except ValueError:
            pass  # corrupt elapsed, still check success below
        if fields[success_idx].strip().lower() != "true":
            failures += 1

    if not elapsed_values:
        return {"samples": 0, "failures": 0, "avg_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0, "rate": 0.0}

    elapsed_values.sort()
    n = len(elapsed_values)
    p95_idx = int(n * 0.95)

    return {
        "samples": n,
        "failures": failures,
        "avg_ms": int(statistics.mean(elapsed_values)),
        "p95_ms": elapsed_values[min(p95_idx, n - 1)],
        "min_ms": elapsed_values[0],
        "max_ms": elapsed_values[-1],
        "rate": (n - failures) / n if n > 0 else 0.0,
    }


def extract_metrics(outcome: dict[str, Any]) -> dict[str, Any]:
    """Auto-detect format and extract metrics from node execution outcome.

    Detects junit XML (contains '<testsuite') vs JMeter JTL (contains 'timeStamp,elapsed').
    Returns empty dict for unrecognized formats.
    """
    stdout = str(outcome.get("stdout", ""))
    if not stdout.strip():
        return {}

    kind = outcome.get("kind", "")
    if kind == "junit" or "<testsuite" in stdout:
        return parse_junit(stdout)
    if kind == "jmeter" or "timeStamp,elapsed" in stdout:
        return parse_jmeter_jtl(stdout)

    return {}
