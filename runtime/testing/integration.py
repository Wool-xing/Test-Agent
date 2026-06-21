"""Integration test executor — API, DB, message queue testing (Sprint 5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IntegrationConfig:
    timeout_seconds: int = 30
    retry_count: int = 2
    base_url: str = ""


@dataclass
class ApiCheck:
    method: str = "GET"
    path: str = "/"
    expected_status: int = 200
    expected_body_contains: str | None = None
    headers: dict = field(default_factory=dict)


@dataclass
class IntegrationResult:
    status: str  # pass | fail | error
    checks: list[dict] = field(default_factory=list)
    summary: str = ""
    error: str | None = None
    duration_ms: int = 0


class IntegrationExecutor:
    """Execute integration tests against APIs, databases, and services."""

    def __init__(self, config: IntegrationConfig | None = None):
        self._config = config or IntegrationConfig()

    def check_api(self, base_url: str, checks: list[ApiCheck]) -> IntegrationResult:
        """Run a series of API endpoint checks."""
        import time
        import urllib.request
        import urllib.error
        import json

        start = time.monotonic()
        results = []
        all_pass = True

        for check in checks:
            url = f"{base_url.rstrip('/')}{check.path}"
            try:
                req = urllib.request.Request(url, method=check.method, headers=check.headers)
                resp = urllib.request.urlopen(req, timeout=self._config.timeout_seconds)
                status_ok = resp.status == check.expected_status
                body = resp.read().decode("utf-8", errors="replace")
                body_ok = check.expected_body_contains is None or check.expected_body_contains in body
                ok = status_ok and body_ok
                results.append({
                    "name": f"{check.method} {check.path}",
                    "expected": f"status={check.expected_status}",
                    "actual": f"status={resp.status} body_len={len(body)}",
                    "pass": ok,
                })
                if not ok:
                    all_pass = False
            except Exception as exc:
                results.append({
                    "name": f"{check.method} {check.path}",
                    "expected": f"status={check.expected_status}",
                    "actual": f"error: {exc}",
                    "pass": False,
                })
                all_pass = False

        return IntegrationResult(
            status="pass" if all_pass else "fail",
            checks=results,
            summary=f"{sum(1 for r in results if r['pass'])}/{len(results)} checks passed",
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def check_db(self, connection_string: str, query: str, expected_rows_min: int = 0) -> IntegrationResult:
        """Execute a database query and verify results.

        Security: query is validated to be SELECT-only with no statement chaining.
        """
        import time
        import re

        # Validate query: SELECT only, no semicolons (prevents statement chaining)
        q = query.strip().upper()
        if not q.startswith("SELECT") or ";" in query:
            return IntegrationResult(
                status="error",
                error="Only SELECT queries without semicolons are allowed",
                duration_ms=0,
            )

        start = time.monotonic()
        try:
            import sqlite3

            conn = sqlite3.connect(connection_string.replace("sqlite:///", ""))
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()

            ok = len(rows) >= expected_rows_min
            return IntegrationResult(
                status="pass" if ok else "fail",
                checks=[{
                    "name": f"DB query: {query[:50]}",
                    "expected": f">={expected_rows_min} rows",
                    "actual": f"{len(rows)} rows",
                    "pass": ok,
                }],
                summary=f"Query returned {len(rows)} rows",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:
            return IntegrationResult(
                status="error",
                error=str(exc),
                summary=f"DB check failed: {exc}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
