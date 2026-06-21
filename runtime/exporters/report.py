"""Report generator — HTML, JSON, JUnit XML formats (Sprint 6)."""

from __future__ import annotations

import json
from pathlib import Path


class ReportGenerator:
    """Generate test reports in multiple formats."""

    def to_html(self, results: list[dict], output_path: str) -> str:
        """Generate an HTML report from test results."""
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")
        total = len(results)

        rows = ""
        for r in results:
            status = r.get("status", "?")
            icon = "✅" if status == "pass" else "❌"
            error = f'<div class="error">{r.get("error", "")}</div>' if r.get("error") else ""
            rows += f"""<tr class="{status}">
                <td>{icon}</td><td>{r.get('name', '?')}</td>
                <td>{r.get('duration_ms', '?')}ms</td>
                <td>{error}</td></tr>"""

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Test Report</title>
<style>body{{font-family:sans-serif;margin:2em}}
.pass{{background:#e6ffe6}}.fail{{background:#ffe6e6}}
.error{{color:#c00;font-size:0.9em}}table{{border-collapse:collapse;width:100%}}
td,th{{padding:8px;border:1px solid #ddd}}</style></head>
<body><h1>Test-Agent Report</h1>
<p>{passed} passed, {failed} failed, {total} total</p>
<table><tr><th></th><th>Name</th><th>Duration</th><th>Error</th></tr>
{rows}</table></body></html>"""

        Path(output_path).write_text(html, encoding="utf-8")
        return output_path

    def to_json(self, results: list[dict], output_path: str) -> str:
        """Generate a JSON report."""
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")
        data = {
            "summary": {"total": len(results), "passed": passed, "failed": failed},
            "results": results,
        }
        Path(output_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def to_junit(self, results: list[dict], output_path: str) -> str:
        """Generate a JUnit XML report for CI integration."""
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")

        cases = ""
        for r in results:
            name = r.get("name", "unknown")
            dur = r.get("duration_ms", 0) / 1000.0
            status = r.get("status", "error")
            if status == "pass":
                cases += f'<testcase name="{name}" time="{dur:.3f}"/>\n'
            else:
                error_msg = r.get("error", "unknown error")
                cases += f'<testcase name="{name}" time="{dur:.3f}"><failure message="{error_msg}"/></testcase>\n'

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="test-agent" tests="{len(results)}" failures="{failed}" errors="0" time="0.0">
{cases}</testsuite>"""

        Path(output_path).write_text(xml, encoding="utf-8")
        return output_path
