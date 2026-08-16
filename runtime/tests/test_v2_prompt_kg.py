"""Tests for runtime/router/v2_prompt.py KG context loader.

Locks the rules:
- graph.json parsed once per file version (mtime-based cache)
- file change → next call reflects new content
- missing/unreadable graph → None, no crash
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.router.v2_prompt import _load_kg_context  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_cache():
    import runtime.router.v2_prompt as v2

    v2._kg_cache = None


class TestKgContext:
    def test_missing_graph_returns_none(self, tmp_path):
        assert _load_kg_context(tmp_path / "nope.json", "login page") is None

    def test_matching_node_returned(self, tmp_path):
        g = tmp_path / "graph.json"
        g.write_text(
            json.dumps({
                "nodes": [
                    {"label": "Login page tests", "norm_label": "login", "community": 1, "source_file": "a.py"}
                ]
            }),
            encoding="utf-8",
        )
        result = _load_kg_context(g, "login page")
        assert result is not None

    def test_graph_reloaded_on_file_change(self, tmp_path):
        """After the graph file changes, the next call must see the new content."""
        g = tmp_path / "graph.json"
        g.write_text(
            json.dumps({
                "nodes": [
                    {"label": "Login page tests", "norm_label": "login", "community": 1, "source_file": "a.py"}
                ]
            }),
            encoding="utf-8",
        )
        _load_kg_context(g, "login")

        g.write_text(
            json.dumps({
                "nodes": [
                    {"label": "Checkout tests", "norm_label": "checkout", "community": 2, "source_file": "b.py"}
                ]
            }),
            encoding="utf-8",
        )
        # Force a deterministic mtime change — rapid rewrites can share an
        # mtime tick on Windows (write-back cache), which would hide the reload.
        import os as _os
        _os.utime(g, (1_000_000_000, 2_000_000_000))

        result = _load_kg_context(g, "checkout")
        assert result is not None
        assert "checkout" in json.dumps(result).lower()
        assert "login" not in json.dumps(result).lower()
