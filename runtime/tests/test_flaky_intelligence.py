# SPDX-License-Identifier: MIT
"""Tests for graph-based flaky test intelligence: root cause, quarantine, fix suggestion."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


def _make_mock_graph() -> dict:
    """Build a minimal mock graph with test nodes, dependencies, and links."""
    return {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": [
            # Flaky test nodes
            {"id": "test_a", "label": "test_a", "norm_label": "test_a",
             "file_type": "code", "source_file": "tests/test_a.py", "community": 1},
            {"id": "test_b", "label": "test_b", "norm_label": "test_b",
             "file_type": "code", "source_file": "tests/test_b.py", "community": 1},
            # Shared dependency (root cause candidate)
            {"id": "shared_db_util", "label": "connect_db()", "norm_label": "connect_db()",
             "file_type": "code", "source_file": "utils/db.py", "community": 2},
            # High-complexity node (many connections)
            {"id": "complex_func", "label": "process_data()", "norm_label": "process_data()",
             "file_type": "code", "source_file": "core/processor.py", "community": 3},
            # Rationale node (should be filtered out)
            {"id": "rationale_1", "label": "why this exists", "norm_label": "why this exists",
             "file_type": "rationale", "source_file": "docs/design.md", "community": 3},
            # Network dep
            {"id": "http_client", "label": "HttpClient.get()", "norm_label": "httpclient.get()",
             "file_type": "code", "source_file": "core/http_client.py", "community": 4},
        ],
        "links": [
            # test_a depends on shared_db_util
            {"source": "test_a", "target": "shared_db_util", "relation": "calls", "weight": 1.0},
            # test_b also depends on shared_db_util (shared root cause)
            {"source": "test_b", "target": "shared_db_util", "relation": "calls", "weight": 1.0},
            # test_b also calls complex_func
            {"source": "test_b", "target": "complex_func", "relation": "calls", "weight": 1.0},
            # complex_func has many edges (high complexity)
            {"source": "complex_func", "target": "http_client", "relation": "calls", "weight": 1.0},
            {"source": "complex_func", "target": "shared_db_util", "relation": "calls", "weight": 1.0},
            {"source": "complex_func", "target": "test_a", "relation": "called_by", "weight": 1.0},
            {"source": "complex_func", "target": "test_b", "relation": "called_by", "weight": 1.0},
            {"source": "complex_func", "target": "rationale_1", "relation": "rationale_for", "weight": 1.0},
            # rationale link (should be ignored in complexity)
            {"source": "shared_db_util", "target": "rationale_1", "relation": "rationale_for", "weight": 1.0},
        ],
        "hyperedges": [],
    }


class TestRootCauseDetection:
    """Tests for find_root_cause_graph with mock graph data."""

    def test_finds_shared_dependency_root_cause(self):
        """Verify that shared dependencies between flaky tests are identified."""
        from utils.quality.flaky_detector import find_root_cause_graph

        graph = _make_mock_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            result = find_root_cause_graph(["test_a", "test_b"], graph_path)
            assert "test_a" in result
            assert "test_b" in result
            # Both tests share shared_db_util — should appear as root cause
            test_a_causes = result["test_a"]
            assert any("shared" in c.lower() or "connect_db" in c.lower()
                       for c in test_a_causes), f"Expected shared dep in causes: {test_a_causes}"
            assert len(test_a_causes) > 0
        finally:
            Path(graph_path).unlink(missing_ok=True)

    def test_missing_graph_returns_graceful_message(self):
        """When the graph file is missing, return a graceful fallback message."""
        from utils.quality.flaky_detector import find_root_cause_graph

        result = find_root_cause_graph(["test_x"], "/nonexistent/graph.json")
        assert "test_x" in result
        assert "graph not available" in result["test_x"][0].lower()

    def test_unknown_test_returns_fallback(self):
        """Tests not found in the graph get a clear message."""
        from utils.quality.flaky_detector import find_root_cause_graph

        graph = _make_mock_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            result = find_root_cause_graph(["completely_unknown_test"], graph_path)
            assert "completely_unknown_test" in result
            assert any("no matching" in c.lower() for c in result["completely_unknown_test"])
        finally:
            Path(graph_path).unlink(missing_ok=True)


class TestAutoQuarantine:
    """Tests for auto_quarantine threshold logic."""

    def test_quarantine_above_threshold(self):
        """Tests that appear >= N times are quarantined."""
        from utils.quality.flaky_detector import auto_quarantine

        # test_a appears 3 times, test_b appears once
        flaky_list = ["test_a", "test_a", "test_a", "test_b"]
        result = auto_quarantine(flaky_list, threshold=3)
        assert "test_a" in result
        assert "test_b" not in result

    def test_quarantine_empty_below_threshold(self):
        """When all tests are below threshold, nothing is quarantined."""
        from utils.quality.flaky_detector import auto_quarantine

        flaky_list = ["test_a", "test_b", "test_c"]
        result = auto_quarantine(flaky_list, threshold=5)
        assert result == []

    def test_quarantine_all_above_threshold(self):
        """When all tests meet threshold, all are quarantined."""
        from utils.quality.flaky_detector import auto_quarantine

        flaky_list = ["test_a", "test_a", "test_b", "test_b"]
        result = auto_quarantine(flaky_list, threshold=2)
        assert set(result) == {"test_a", "test_b"}

    def test_quarantine_empty_list(self):
        """Empty list returns empty quarantine."""
        from utils.quality.flaky_detector import auto_quarantine

        result = auto_quarantine([], threshold=3)
        assert result == []


class TestSuggestFix:
    """Tests for suggest_fix based on graph analysis."""

    def test_suggests_db_fix_when_db_deps_present(self):
        """When test depends on DB-related nodes, suggest DB fix strategies."""
        from utils.quality.flaky_detector import suggest_fix

        graph = {
            "directed": False, "multigraph": False, "graph": {},
            "nodes": [
                {"id": "test_db_flaky", "label": "test_db_flaky", "norm_label": "test_db_flaky",
                 "file_type": "code", "source_file": "tests/test_db.py", "community": 1},
                {"id": "db_connect", "label": "database.connect()", "norm_label": "database.connect()",
                 "file_type": "code", "source_file": "db/connection.py", "community": 2},
            ],
            "links": [
                {"source": "test_db_flaky", "target": "db_connect", "relation": "calls", "weight": 1.0},
            ],
            "hyperedges": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            suggestion = suggest_fix("test_db_flaky", graph_path)
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
            assert any(kw in suggestion.lower() for kw in
                       ["database", "transaction", "rollback", "seed", "connection pool"])
        finally:
            Path(graph_path).unlink(missing_ok=True)

    def test_suggests_network_fix_when_http_deps_present(self):
        """When test depends on network/HTTP nodes, suggest mocking."""
        from utils.quality.flaky_detector import suggest_fix

        graph = {
            "directed": False, "multigraph": False, "graph": {},
            "nodes": [
                {"id": "test_api", "label": "test_api_call", "norm_label": "test_api_call",
                 "file_type": "code", "source_file": "tests/test_api.py", "community": 1},
                {"id": "http_client", "label": "HttpClient.request()", "norm_label": "httpclient.request()",
                 "file_type": "code", "source_file": "http/client.py", "community": 4},
            ],
            "links": [
                {"source": "test_api", "target": "http_client", "relation": "calls", "weight": 1.0},
            ],
            "hyperedges": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            suggestion = suggest_fix("test_api_call", graph_path)
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
            assert any(kw in suggestion.lower() for kw in
                       ["mock", "http", "network", "retry"])
        finally:
            Path(graph_path).unlink(missing_ok=True)

    def test_suggest_fix_no_graph_fallback(self):
        """When graph is missing, returns general fix suggestions."""
        from utils.quality.flaky_detector import suggest_fix

        suggestion = suggest_fix("unknown_test", "/nonexistent/graph.json")
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0
        assert "available" in suggestion.lower() or "isolation" in suggestion.lower()
