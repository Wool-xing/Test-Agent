"""Shared pytest fixtures for runtime."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _env_isolation(tmp_path: Path, monkeypatch):
    """Isolate each test from real DB/MinIO/Prefect + reset shared state."""
    monkeypatch.setenv("TAGENT_DB_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("TAGENT_OTEL_ENABLED", "false")
    if os.environ.get("TAGENT_REAL_LLM") != "1":
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("TAGENT_WORKSPACE_DIR", str(tmp_path / "workspace"))

    # Reset catalog cache to prevent cross-test state pollution
    from runtime.registry.registry import get_catalog
    get_catalog(refresh=True)

    # Reset runtime settings cache (may have been built under stale env)
    import runtime.config.settings as _s
    _s._settings = None

    yield


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]
