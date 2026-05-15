"""Shared pytest fixtures for runtime."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _env_isolation(tmp_path: Path, monkeypatch):
    """Isolate each test from real DB/MinIO/Prefect.

    TAGENT_REAL_LLM=1 时保留外部 TAGENT_LLM_PROVIDER (test_router_real 等真 LLM 测试用).
    """
    monkeypatch.setenv("TAGENT_DB_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("TAGENT_OTEL_ENABLED", "false")
    if os.environ.get("TAGENT_REAL_LLM") != "1":
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "stub")
    monkeypatch.setenv("TAGENT_WORKSPACE_DIR", str(tmp_path / "workspace"))
    yield


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]
