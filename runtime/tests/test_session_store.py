"""Tests for cross-session learning loop: SessionStore, PatternExtractor, Curator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from runtime.learning.session_store import SessionRecord, SessionStore
from runtime.learning.pattern_extractor import PatternExtractor
from runtime.learning.curator import Curator


# ── helpers ───────────────────────────────────────────────────────

def _make_session(
    session_id: str,
    target: str = "web login test",
    outcomes: dict | None = None,
    agent_decisions: list[dict] | None = None,
    dag_results: list[dict] | None = None,
    routing_decision: dict | None = None,
    human_feedback: str | None = None,
) -> SessionRecord:
    return SessionRecord(
        id=session_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        target=target,
        routing_decision=routing_decision or {
            "detected_target_type": "web-system",
            "nodes": [
                {"name": "requirements-analyst", "kind": "agent"},
                {"name": "automation-engineer", "kind": "agent"},
                {"name": "test-executor", "kind": "agent"},
            ],
        },
        dag_results=dag_results or [
            {"node": "requirements-analyst", "status": "ok", "error": ""},
            {"node": "automation-engineer", "status": "ok", "error": ""},
            {"node": "test-executor", "status": "ok", "error": ""},
        ],
        outcomes=outcomes or {"passed": 8, "failed": 2, "skipped": 0},
        agent_decisions=agent_decisions or [
            {"agent": "requirements-analyst", "decision": "analyze", "ts": "2026-01-01T00:00:00Z"},
            {"agent": "automation-engineer", "decision": "generate", "ts": "2026-01-01T00:01:00Z"},
            {"agent": "test-executor", "decision": "execute", "ts": "2026-01-01T00:02:00Z"},
        ],
        human_feedback=human_feedback,
    )


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_sessions.db"


# ── test 1: save + retrieve ───────────────────────────────────────

def test_save_and_retrieve_session(db_path: Path):
    """Save a session and retrieve it by id."""
    store = SessionStore(db_path)
    s = _make_session("s1", target="API auth test")
    store.save_session(s)

    loaded = store.get_session("s1")
    assert loaded is not None
    assert loaded.id == "s1"
    assert loaded.target == "API auth test"
    assert loaded.outcomes == {"passed": 8, "failed": 2, "skipped": 0}
    assert len(loaded.agent_decisions) == 3
    assert loaded.agent_decisions[0]["agent"] == "requirements-analyst"


# ── test 2: FTS5 search ───────────────────────────────────────────

def test_fts5_search(db_path: Path):
    """FTS5 full-text search finds sessions by target content."""
    store = SessionStore(db_path)
    store.save_session(_make_session("a1", target="login page test"))
    store.save_session(_make_session("a2", target="payment gateway test"))
    store.save_session(_make_session("a3", target="login API auth test"))

    results = store.search("login", limit=10)
    assert len(results) == 2
    ids = {r.id for r in results}
    assert ids == {"a1", "a3"}


# ── test 3: find similar sessions ─────────────────────────────────

def test_find_similar_sessions(db_path: Path):
    """find_similar returns sessions with matching target keywords."""
    store = SessionStore(db_path)
    store.save_session(_make_session("b1", target="web application login test"))
    store.save_session(_make_session("b2", target="desktop app UI test"))
    store.save_session(_make_session("b3", target="web application payment test"))

    similar = store.find_similar("web application", limit=5)
    assert len(similar) == 2
    ids = {r.id for r in similar}
    assert ids == {"b1", "b3"}


# ── test 4: stats aggregation ─────────────────────────────────────

def test_stats_aggregation(db_path: Path):
    """get_stats aggregates outcomes across sessions in the date range."""
    store = SessionStore(db_path)
    store.save_session(_make_session("c1", outcomes={"passed": 5, "failed": 1, "skipped": 0}))
    store.save_session(_make_session("c2", outcomes={"passed": 10, "failed": 0, "skipped": 2}))
    store.save_session(_make_session("c3", outcomes={"passed": 3, "failed": 3, "skipped": 0}))

    stats = store.get_stats(days=365)
    assert stats["total_sessions"] == 3
    assert stats["total_passed"] == 18
    assert stats["total_failed"] == 4
    assert stats["total_skipped"] == 2
    assert stats["total_cases"] == 24
    assert stats["pass_rate_pct"] == 75.0


# ── test 5: recent listing ────────────────────────────────────────

def test_list_recent(db_path: Path):
    """list_recent returns sessions ordered by created_at descending."""
    store = SessionStore(db_path)

    # Insert with explicit timestamps so ordering is deterministic
    for i in range(5):
        s = _make_session(f"r{i}")
        s.created_at = f"2026-06-{19 - i:02d}T10:00:00Z"
        store.save_session(s)

    recent = store.list_recent(limit=3)
    assert len(recent) == 3
    # Most recent first
    assert recent[0].id == "r0"
    assert recent[1].id == "r1"
    assert recent[2].id == "r2"


# ── test 6: pattern extraction ────────────────────────────────────

def test_pattern_extraction_from_multiple_sessions():
    """PatternExtractor detects repeated agent sequences and skill candidates."""
    sessions = [
        _make_session("p1", target="web app login test", agent_decisions=[
            {"agent": "requirements-analyst", "decision": "a"},
            {"agent": "automation-engineer", "decision": "b"},
        ]),
        _make_session("p2", target="web app login test", agent_decisions=[
            {"agent": "requirements-analyst", "decision": "a"},
            {"agent": "automation-engineer", "decision": "b"},
        ]),
        _make_session("p3", target="web app login test", agent_decisions=[
            {"agent": "requirements-analyst", "decision": "a"},
            {"agent": "automation-engineer", "decision": "b"},
        ]),
        _make_session("p4", target="api gateway test", agent_decisions=[
            {"agent": "mobile-tester", "decision": "x"},
        ]),
        _make_session("p5", target="api gateway test", agent_decisions=[
            {"agent": "mobile-tester", "decision": "x"},
        ]),
    ]

    extractor = PatternExtractor()
    patterns = extractor.extract(sessions)

    # Should detect the agent sequence pattern (3 out of 5 sessions)
    agent_seqs = [p for p in patterns if p["type"] == "agent_sequence"]
    assert len(agent_seqs) >= 1
    high_conf = [p for p in agent_seqs if p["confidence"] >= 0.5]
    assert len(high_conf) >= 1

    # Should detect skill candidates
    skill_cands = [p for p in patterns if p["type"] == "skill_candidate"]
    assert len(skill_cands) >= 1

    # Verify pattern structure
    for p in patterns:
        assert "type" in p
        assert "description" in p
        assert "confidence" in p
        assert "evidence" in p
        assert "detail" in p
        assert 0.0 <= p["confidence"] <= 1.0


# ── test 7: curator cycle ─────────────────────────────────────────

def test_curator_cycle(tmp_path: Path):
    """Curator runs a cycle without modifying real files (uses tmp_path)."""
    db_path = tmp_path / "curator_test.db"
    learned_dir = tmp_path / "learned_skills"
    store = SessionStore(db_path)

    # Seed sessions with a repeated pattern
    for i in range(5):
        s = _make_session(
            f"cur{i}",
            target=f"repeated API integration test #{i}",
            agent_decisions=[
                {"agent": "requirements-analyst", "decision": "analyze"},
                {"agent": "automation-engineer", "decision": "generate"},
                {"agent": "test-executor", "decision": "execute"},
            ],
        )
        store.save_session(s)

    curator = Curator(
        store,
        accept_threshold=0.5,  # lower threshold to ensure acceptance
        cycle_days=365,
        max_accepted=5,
        learned_skills_dir=learned_dir,
    )

    result = curator.run_cycle()

    assert result["sessions_scanned"] == 5
    assert result["accepted"] >= 0
    assert result["rejected"] >= 0
    assert "cycle_ts" in result
    assert "notes" in result

    # If any skills were accepted, verify manifests were written
    if result["accepted"] > 0:
        assert learned_dir.is_dir()
        skill_dirs = list(learned_dir.iterdir())
        assert len(skill_dirs) >= 1
        manifest_file = skill_dirs[0] / "manifest.yaml"
        assert manifest_file.is_file()
        manifest = manifest_file.read_text(encoding="utf-8")
        assert "name:" in manifest
        assert "auto-learned" in manifest


# ── test 8: curator with no sessions ──────────────────────────────

def test_curator_empty_cycle(tmp_path: Path):
    """Curator handles empty session store gracefully."""
    db_path = tmp_path / "empty_test.db"
    learned_dir = tmp_path / "empty_learned"
    store = SessionStore(db_path)

    curator = Curator(store, learned_skills_dir=learned_dir)
    result = curator.run_cycle()

    assert result["accepted"] == 0
    assert result["rejected"] == 0
    assert result["pending"] == 0
    assert result["sessions_scanned"] == 0
    assert len(result["notes"]) >= 1
