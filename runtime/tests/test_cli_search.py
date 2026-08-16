"""Tests for runtime/cli/search.py.

Locks the rules:
- index_session batches: one connection per session, not one per message
- search() finds indexed content
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.cli import search as search_mod  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(search_mod, "_SEARCH_DB", tmp_path / "search.db")


class TestIndexSessionBatching:
    def test_one_connection_per_session(self, monkeypatch):
        """index_session must open the DB once, regardless of message count."""
        calls = []

        real_ensure = search_mod._ensure_db

        def counting_ensure():
            calls.append(1)
            return real_ensure()

        monkeypatch.setattr(search_mod, "_ensure_db", counting_ensure)

        messages = [
            {"role": "user", "content": f"hello message {i}", "ts": ""}
            for i in range(5)
        ]
        count = search_mod.index_session("sess-1", messages)
        assert count == 5
        assert len(calls) == 1

    def test_indexed_messages_searchable(self):
        search_mod.index_session(
            "sess-1",
            [
                {"role": "user", "content": "run smoke test on login page", "ts": ""},
                {"role": "assistant", "content": "login page covered", "ts": ""},
            ],
        )
        results = search_mod.search("login")
        assert any("login" in r["content"] for r in results)

    def test_empty_content_skipped(self):
        count = search_mod.index_session(
            "sess-2",
            [
                {"role": "user", "content": "   ", "ts": ""},
                {"role": "user", "content": "real content", "ts": ""},
            ],
        )
        assert count == 1
