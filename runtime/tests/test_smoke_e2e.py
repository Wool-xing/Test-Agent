"""End-to-end smoke: stub LLM -> router -> orchestrator -> flow summary.

Does NOT require docker compose; uses sqlite in tmp + stub provider + no real
external services. Verifies the runtime wires up end-to-end.
"""

from __future__ import annotations

from runtime.api.deps import Kernel
from runtime.api.parsers import parse_text


def test_e2e_web_target_runs(monkeypatch):
    monkeypatch.setenv("TAGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("TAGENT_LLM_PROVIDER_FALLBACK", "stub")
    kernel = Kernel()
    art = parse_text("Please test the Web system at https://demo.example.com login + checkout flows")
    run_id, decision = kernel.submit(art, persist=False)
    assert decision.detected_target_type == "web-system"
    assert decision.dag, "router produced empty DAG"
    summary = kernel.execute_sync(run_id, decision)
    assert summary["total"] == len(decision.dag)
    # smoke goal: flow returns a summary dict; some nodes may be no-ops (mapped to None script).
    assert "succeeded" in summary
    assert "failed" in summary
    assert "results" in summary


def test_e2e_api_target_routes_automation_engineer(monkeypatch):
    monkeypatch.setenv("TAGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("TAGENT_LLM_PROVIDER_FALLBACK", "stub")
    kernel = Kernel()
    art = parse_text("REST API endpoints /v1/orders /v1/users gRPC + WebSocket")
    _, decision = kernel.submit(art, persist=False)
    names = [n.name for n in decision.dag]
    assert "automation-engineer" in names
    assert "report-generator" in names
