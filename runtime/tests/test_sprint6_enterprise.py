"""TDD: Sprint 6 — 多LLM + 报告 + 通知."""

from __future__ import annotations

import json
import pytest


class TestMultiLLM:
    """Multi-LLM provider support."""

    def test_provider_config_validates(self):
        """Provider config should accept known providers."""
        from runtime.router.llm_client import LLMClient
        for provider in ["openai", "anthropic", "deepseek", "gemini", "ollama", "stub"]:
            client = LLMClient(provider=provider)
            assert client.provider == provider

    def test_fallback_provider_works(self):
        """Fallback provider should be set."""
        from runtime.router.llm_client import LLMClient
        client = LLMClient(provider="openai", fallback="stub")
        assert client.provider == "openai"
        assert client.fallback == "stub"


class TestReportSystem:
    """HTML/JSON/JUnit report generation."""

    def test_html_report_generates(self, tmp_path):
        """HTML report should generate valid HTML file."""
        from runtime.exporters.report import ReportGenerator
        gen = ReportGenerator()
        results = [
            {"name": "test1", "status": "pass", "duration_ms": 100},
            {"name": "test2", "status": "fail", "duration_ms": 200, "error": "assertion failed"},
        ]
        path = gen.to_html(results, str(tmp_path / "report.html"))
        with open(path, encoding="utf-8") as f:
            html = f.read()
        assert "<html" in html
        assert "test1" in html
        assert "test2" in html

    def test_json_report_generates(self, tmp_path):
        """JSON report should be valid JSON."""
        from runtime.exporters.report import ReportGenerator
        gen = ReportGenerator()
        results = [{"name": "test1", "status": "pass"}]
        path = gen.to_json(results, str(tmp_path / "report.json"))
        data = json.loads(open(path).read())
        assert data["summary"]["total"] == 1
        assert data["results"][0]["name"] == "test1"

    def test_junit_report_generates(self, tmp_path):
        """JUnit XML report should be valid XML."""
        from runtime.exporters.report import ReportGenerator
        gen = ReportGenerator()
        results = [{"name": "test1", "status": "pass", "duration_ms": 100}]
        path = gen.to_junit(results, str(tmp_path / "report.xml"))
        with open(path, encoding="utf-8") as f:
            xml = f.read()
        assert "<?xml" in xml
        assert 'testsuite' in xml
        assert 'test1' in xml
