"""Verify build_artifact: path / url / text input parsing."""

from __future__ import annotations

import tempfile
from pathlib import Path

from runtime.cli._shared import build_artifact


def test_build_artifact_url():
    """URL targets are parsed as web artifacts."""
    art = build_artifact("https://example.com/api", "")
    assert art.kind == "url"
    assert "example.com" in art.text


def test_build_artifact_existing_file():
    """Existing file paths are parsed by path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Test PRD\n## Feature 1")
        tmp = f.name
    try:
        art = build_artifact(tmp, "")
        assert art.kind == "file"
        assert "Test PRD" in (art.text or "")
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_build_artifact_free_text():
    """Free-form text is parsed as text artifact."""
    art = build_artifact("test the login module", "")
    assert art.kind == "text"
    assert "login" in art.text


def test_build_artifact_with_note():
    """Note is appended to artifact text."""
    art = build_artifact("test login", "verify session timeout")
    assert "session timeout" in art.text
    assert "login" in art.text
