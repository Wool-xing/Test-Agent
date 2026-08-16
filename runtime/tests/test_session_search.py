"""Tests for runtime/learning_loop/session_search.py.

Locks the rule: DDL runs once per process, not on every call.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.learning_loop import session_search as ss  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "_db_path", lambda: tmp_path / "sessions.db")
    ss._initialized = False


class TestSessionSearch:
    def test_init_db_runs_once(self, monkeypatch):
        calls = []
        real_conn = ss._conn

        def counting_conn():
            calls.append(1)
            return real_conn()

        monkeypatch.setattr(ss, "_conn", counting_conn)
        ss._init_db()
        ss._init_db()
        assert len(calls) == 1

    def test_index_and_search_roundtrip(self):
        ss.index_session("s1", "r1", "web", "login page smoke test failed")
        results = ss.search("login")
        assert any(r["session_id"] == "s1" for r in results)

    def test_get_meta_after_attach_summary(self):
        ss.index_session("s2", "r2", "web", "checkout flow")
        ss.attach_summary("s2", "checkout has 3 bugs")
        meta = ss.get_meta("s2")
        assert meta is not None
        assert meta["summary"] == "checkout has 3 bugs"
