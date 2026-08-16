"""Verify /status/{run_id}: unknown runs must 404, never fake "running"."""

from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.api.main import app

client = TestClient(app)


def test_status_unknown_run_returns_404():
    """GET /status for a run_id that never existed must return 404."""
    resp = client.get("/status/no-such-run-000000000000")
    assert resp.status_code == 404
    assert "run not found" in resp.json()["detail"]


def test_status_active_run_reports_running():
    """A run registered as active but not finished reports 'running'."""
    from runtime.api.main import _run_active, _run_lock

    run_id = "active-run-00000000000001"
    import time as _time
    with _run_lock:
        _run_active[run_id] = _time.time()
    try:
        resp = client.get(f"/status/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
    finally:
        with _run_lock:
            _run_active.pop(run_id, None)


def test_status_completed_run_reports_final_state():
    """A finished run reports succeeded/failed, not 'running'."""
    from runtime.api.main import _run_results

    run_id = "done-run-00000000000001"
    _run_results.put(run_id, {"failed": 0, "succeeded": 1, "total": 1})
    try:
        resp = client.get(f"/status/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "succeeded"
    finally:
        _run_results.remove(run_id)


def test_run_rejected_when_at_concurrency_limit(monkeypatch):
    """max_concurrent_runs must be enforced: full capacity → 429."""
    from types import SimpleNamespace

    from runtime.api.main import _kernel, _run_active, _run_lock, _settings

    monkeypatch.setattr(_settings, "max_concurrent_runs", 1)
    fake_decision = SimpleNamespace(
        detected_target_type="web",
        detected_qualities=[],
        confidence=0.9,
        rationale="test",
        dag=[],
    )
    submit_calls = []

    def counting_submit(art, persist=True):
        submit_calls.append(1)
        return ("fake-run-id", fake_decision)

    monkeypatch.setattr(_kernel, "submit", counting_submit)

    import time as _time
    with _run_lock:
        _run_active["busy-run-0000000000001"] = _time.time()
    try:
        resp = client.post("/run/text", json={"text": "run smoke test"})
        assert resp.status_code == 429
        assert submit_calls == [], "at capacity, kernel.submit (LLM routing) must NOT run"
    finally:
        with _run_lock:
            _run_active.pop("busy-run-0000000000001", None)


def test_run_file_rejects_oversize_upload(monkeypatch):
    """UploadFile max size must be enforced in the endpoint (File max_length does not apply)."""
    import runtime.api.main as main_mod

    monkeypatch.setattr(main_mod, "_MAX_UPLOAD_BYTES", 10)
    resp = client.post(
        "/run/file",
        files={"file": ("big.md", b"x" * 100, "text/markdown")},
    )
    assert resp.status_code == 413


def test_run_text_sanitizes_prompt(monkeypatch):
    """prompt_guard.sanitize_input must run on /run/text input (injection defense)."""
    from types import SimpleNamespace

    from runtime.api.main import _kernel

    captured: dict = {}

    def fake_submit(art, persist=True):
        captured["text"] = art.text
        fake_decision = SimpleNamespace(
            detected_target_type="web",
            detected_qualities=[],
            confidence=0.9,
            rationale="test",
            dag=[],
        )
        return ("fake-id-00000000000001", fake_decision)

    monkeypatch.setattr(_kernel, "submit", fake_submit)
    resp = client.post("/run/text", json={"text": "hello\x00world\x1f"})
    assert resp.status_code == 200
    assert "\x00" not in captured["text"]
    assert "\x1f" not in captured["text"]
