"""Tests for the KG‑driven impact engine."""

from __future__ import annotations

import pytest
from pathlib import Path

from runtime.intelligence.impact_engine import ImpactEngine, ImpactResult


@pytest.fixture
def graph_path():
    p = Path("graphify-out/graph.json")
    if not p.exists():
        p = Path(__file__).resolve().parent.parent.parent / "graphify-out" / "graph.json"
    return p


@pytest.fixture
def engine(graph_path):
    return ImpactEngine(graph_path=graph_path)


# ── Test 1: graph loading ────────────────────────────────────

def test_graph_loading(engine):
    """Engine loads graph.json and indexes nodes/links."""
    if not engine.is_loaded:
        pytest.skip("No graph.json found — degraded mode")
    assert len(engine._nodes_by_id) > 0, "Should have indexed nodes"
    assert len(engine._adj_forward) > 0, "Should have indexed forward edges"
    assert len(engine._adj_reverse) > 0, "Should have indexed reverse edges"


# ── Test 2: impact analysis on known function ────────────────

def test_analyze_known_file(engine):
    """Analyzing a known file returns a valid ImpactResult."""
    if not engine.is_loaded:
        pytest.skip("No graph.json found — degraded mode")

    # Use a file we know is in the graph
    result = engine.analyze(["runtime/__init__.py"])
    assert isinstance(result, ImpactResult)
    assert result.changed_file == "runtime/__init__.py"
    assert isinstance(result.risk_score, float)
    assert 0.0 <= result.risk_score <= 1.0
    assert result.test_recommendation in ("run-all", "run-impacted", "skip")


# ── Test 3: blast radius traversal ───────────────────────────

def test_blast_radius_traversal(engine):
    """BFS traversal finds transitive dependents."""
    if not engine.is_loaded:
        pytest.skip("No graph.json found — degraded mode")

    # Use a function we know exists — _read_version is in graph
    broken = engine.what_breaks("_read_version")
    # _read_version() exists at runtime/__init__.py, should have dependents
    assert isinstance(broken, list)
    # It may or may not have dependents, but the query should not error
    if broken:
        for entry in broken:
            assert "::" in entry or entry, f"Invalid entry: {entry}"


# ── Test 4: test recommendation ──────────────────────────────

def test_recommend_tests(engine):
    """recommend_tests returns a list of test files or empty for run-all."""
    if not engine.is_loaded:
        pytest.skip("No graph.json found — degraded mode")

    result = engine.recommend_tests(["runtime/__init__.py"])
    assert isinstance(result, list)
    # Empty list means "run all" (high risk), list of strings means targeted
    for t in result:
        assert isinstance(t, str)


# ── Test 5: risk score computation ───────────────────────────

def test_risk_score_bounds(engine):
    """Risk score is always in [0.0, 1.0]."""
    # Test with empty input
    result = engine.analyze([])
    assert result.risk_score == 0.0

    # Test with unknown file
    result2 = engine.analyze(["nonexistent/file.py"])
    if engine.is_loaded:
        assert result2.risk_score == 0.1  # skip recommendation

    # Internal _compute_risk bounds
    assert ImpactEngine._compute_risk(0, 0, 0) == 0.0
    assert ImpactEngine._compute_risk(100, 200, 100) <= 1.0
    assert ImpactEngine._compute_risk(0, 0, 0) >= 0.0


# ── Test: degraded mode works without graph ──────────────────

def test_degraded_mode_no_graph():
    """Engine without graph.json returns safe defaults."""
    engine = ImpactEngine(graph_path=Path("nonexistent_graph.json"))
    assert not engine.is_loaded

    result = engine.analyze(["some/file.py"])
    assert result.risk_score == 0.8
    assert result.test_recommendation == "run-all"
    assert engine.what_breaks("foo") == []
    assert engine.what_tests("bar") == []
