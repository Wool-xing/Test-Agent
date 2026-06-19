# SPDX-License-Identifier: MIT
"""Tests for KG Dashboard REST API endpoints."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def _make_minimal_graph() -> dict:
    """Build a minimal graph for API testing."""
    return {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": [
            {"id": "n1", "label": "alpha_func", "norm_label": "alpha_func",
             "file_type": "code", "source_file": "src/alpha.py", "source_location": "L10",
             "community": 1},
            {"id": "n2", "label": "beta_func", "norm_label": "beta_func",
             "file_type": "code", "source_file": "src/beta.py", "source_location": "L20",
             "community": 1},
            {"id": "n3", "label": "gamma_util", "norm_label": "gamma_util",
             "file_type": "code", "source_file": "utils/gamma.py", "source_location": "L5",
             "community": 2},
            {"id": "r1", "label": "design rationale", "norm_label": "design rationale",
             "file_type": "rationale", "source_file": "docs/design.md", "source_location": "L1",
             "community": 1},
        ],
        "links": [
            {"source": "n1", "target": "n3", "relation": "calls", "weight": 1.0,
             "confidence": "EXTRACTED", "confidence_score": 1.0,
             "source_file": "src/alpha.py", "source_location": "L12"},
            {"source": "n2", "target": "n3", "relation": "calls", "weight": 1.0,
             "confidence": "EXTRACTED", "confidence_score": 1.0,
             "source_file": "src/beta.py", "source_location": "L22"},
            {"source": "n1", "target": "n2", "relation": "imports", "weight": 1.0,
             "confidence": "EXTRACTED", "confidence_score": 1.0,
             "source_file": "src/alpha.py", "source_location": "L1"},
            {"source": "n3", "target": "r1", "relation": "rationale_for", "weight": 1.0,
             "confidence": "EXTRACTED", "confidence_score": 1.0,
             "source_file": "utils/gamma.py", "source_location": "L5"},
        ],
        "hyperedges": [],
    }


class TestKgStatsEndpoint:
    def test_stats_returns_valid_response(self):
        """/api/kg/stats returns graph statistics with expected keys."""
        from runtime.web.kg_api import _graph_cache

        # Clear cache and inject mock
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from runtime.web.kg_api import kg_stats
                result = kg_stats()

            assert isinstance(result, dict)
            assert result["node_count"] == 4
            assert result["link_count"] == 4
            assert result["hyperedge_count"] == 0
            assert result["community_count"] == 2
            assert "code" in result["file_types"]
            assert "rationale" in result["file_types"]
            assert len(result["top_nodes"]) > 0
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)

    def test_stats_graph_missing_returns_503(self):
        """When graph file is missing, returns 503 via HTTPException."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", "/nonexistent/graph.json"):
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    from runtime.web.kg_api import kg_stats
                    kg_stats()
                assert exc_info.value.status_code == 503
        finally:
            kg_mod._graph_cache = None


class TestKgSearchEndpoint:
    def test_search_returns_matches(self):
        """/api/kg/search returns nodes matching the query string."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from runtime.web.kg_api import search_nodes
                result = search_nodes(q="alpha")

            assert isinstance(result, dict)
            assert result["query"] == "alpha"
            assert result["total_matches"] >= 1
            assert any("alpha" in r["label"].lower() for r in result["results"])
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)

    def test_search_no_matches_returns_empty(self):
        """Searching for a non-existent term returns empty results."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from runtime.web.kg_api import search_nodes
                result = search_nodes(q="zzz_nonexistent_xyz")

            assert result["total_matches"] == 0
            assert result["results"] == []
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)


class TestKgPathEndpoint:
    def test_path_between_connected_nodes(self):
        """Finding path between two connected nodes returns the path."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from runtime.web.kg_api import find_path
                result = find_path(from_node="n1", to_node="n2")

            assert result["found"] is True
            assert result["length"] == 1  # n1 -> n2 is direct
            # n1 and n2 should be in the path
            path_ids = [p["id"] for p in result["path"]]
            assert "n1" in path_ids
            assert "n2" in path_ids
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)

    def test_path_nonexistent_node_returns_404(self):
        """Searching path from a non-existent node returns 404."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    from runtime.web.kg_api import find_path
                    find_path(from_node="nonexistent_node", to_node="n1")
                assert exc_info.value.status_code == 404
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)


class TestKgNeighborsEndpoint:
    def test_neighbors_returns_connected_nodes(self):
        """Neighbors endpoint returns directly connected nodes."""
        import runtime.web.kg_api as kg_mod
        kg_mod._graph_cache = None

        graph = _make_minimal_graph()
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(graph, f)
            graph_path = f.name

        try:
            with patch.object(kg_mod, "DEFAULT_GRAPH_PATH", graph_path):
                from runtime.web.kg_api import neighbors
                result = neighbors(node_id="n1", depth=1)

            assert result["node_id"] == "n1"
            assert result["neighbor_count"] >= 1
            neighbor_ids = [n["id"] for n in result["neighbors"]]
            # n1 is connected to n2 and n3
            assert "n2" in neighbor_ids or "n3" in neighbor_ids
        finally:
            kg_mod._graph_cache = None
            Path(graph_path).unlink(missing_ok=True)
