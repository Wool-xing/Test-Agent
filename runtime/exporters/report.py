"""Report generator — HTML, JSON, JUnit XML formats (Sprint 6)."""

from __future__ import annotations

import html as _html
import json
import xml.sax.saxutils as _xmlutils
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
            status = _html.escape(r.get("status", "?"))
            icon = "&#x2705;" if r.get("status") == "pass" else "&#x274C;"
            name = _html.escape(str(r.get("name", "?")))
            dur = r.get("duration_ms", "?")
            error_text = _html.escape(str(r.get("error", ""))) if r.get("error") else ""
            error = f'<div class="error">{error_text}</div>' if error_text else ""
            rows += f"""<tr class="{status}">
                <td>{icon}</td><td>{name}</td>
                <td>{dur}ms</td>
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

    def to_pdf(self, results: list[dict], output_path: str) -> str:
        """Generate a PDF report (requires fpdf2). Falls back to HTML if unavailable."""
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")
        total = len(results)

        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(200, 10, text="Test-Agent Report", align="C")
            pdf.ln()
            pdf.set_font("Helvetica", size=10)
            pdf.cell(200, 8, text=f"Passed: {passed}  Failed: {failed}  Total: {total}")
            pdf.ln(12)
            for r in results:
                status = r.get("status", "?")
                name = r.get("name", "?")
                pdf.cell(200, 7, text=f"[{'PASS' if status == 'pass' else 'FAIL'}] {name}")
                pdf.ln()
            pdf.output(output_path)
            return output_path
        except ImportError:
            # Fall back to HTML
            html_path = output_path.replace(".pdf", ".html")
            return self.to_html(results, html_path)

    def to_junit(self, results: list[dict], output_path: str) -> str:
        """Generate a JUnit XML report for CI integration."""
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")

        cases = ""
        for r in results:
            name = _xmlutils.escape(str(r.get("name", "unknown")))
            dur = r.get("duration_ms", 0) / 1000.0
            status = r.get("status", "error")
            if status == "pass":
                cases += f'<testcase name="{name}" time="{dur:.3f}"/>\n'
            else:
                error_msg = _xmlutils.escape(str(r.get("error", "unknown error")))
                cases += f'<testcase name="{name}" time="{dur:.3f}"><failure message="{error_msg}"/></testcase>\n'

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="test-agent" tests="{len(results)}" failures="{failed}" errors="0" time="0.0">
{cases}</testsuite>"""

        Path(output_path).write_text(xml, encoding="utf-8")
        return output_path
