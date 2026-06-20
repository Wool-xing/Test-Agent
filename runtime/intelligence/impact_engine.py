"""KG‑driven impact analysis engine — blast radius in one call.

Queries the graphify-out/graph.json knowledge graph to compute:
  - What depends on a changed file/function (blast radius)
  - Which test files are impacted
  - Composite risk score
  - Actionable test recommendations

Inspired by GitNexus's "blast radius in 1 call" pattern.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Relations the engine follows when traversing dependencies.
# "inbound" = if A imports B, changing B affects A (reverse edge).
_TRANSITIVE_RELATIONS: set[str] = {
    "calls",
    "uses",
    "imports",
    "imports_from",
    "references",
    "contains",
    "defines",
    "implements",
    "shares_data_with",
    "inherits",
    "method",
}

# Relations that imply a structural link (file → symbol or symbol → file).
_CONTAINS_RELATIONS: set[str] = {"contains", "defines"}


@dataclass
class ImpactResult:
    changed_file: str
    affected_functions: list[str] = field(default_factory=list)
    blast_radius: list[str] = field(default_factory=list)
    impacted_tests: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    test_recommendation: str = "skip"  # "run-all" | "run-impacted" | "skip"


class ImpactEngine:
    """Queries the knowledge graph for impact analysis."""

    def __init__(self, graph_path: Path | None = None):
        self.graph_path = graph_path or Path("graphify-out/graph.json")
        self.graph: dict | None = None
        self._nodes_by_id: dict[str, dict] = {}
        self._nodes_by_file: dict[str, list[str]] = {}  # source_file → [node_id, ...]
        self._adj_forward: dict[str, list[tuple[str, str]]] = {}  # node_id → [(relation, target_id)]
        self._adj_reverse: dict[str, list[tuple[str, str]]] = {}  # node_id → [(relation, source_id)]
        self._test_node_ids: set[str] = set()

        if self.graph_path.exists():
            self._load_graph()

    # ── loading ──────────────────────────────────────────────

    def _load_graph(self) -> None:
        """Load graph.json and build in‑memory indexes."""
        try:
            raw = json.loads(self.graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load graph.json: %s", exc)
            return

        self.graph = raw

        # Index nodes
        for node in raw.get("nodes", []):
            nid = node.get("id", "")
            if not nid:
                continue
            self._nodes_by_id[nid] = node
            sf = node.get("source_file", "")
            if sf:
                self._nodes_by_file.setdefault(sf, []).append(nid)
            # Identify test nodes
            if "test" in sf.lower() or "test_" in node.get("label", "").lower():
                self._test_node_ids.add(nid)

        # Index edges (bidirectional for forward/reverse traversal)
        for link in raw.get("links", []):
            rel = link.get("relation", "")
            src = link.get("source", "")
            tgt = link.get("target", "")
            if not src or not tgt:
                continue
            self._adj_forward.setdefault(src, []).append((rel, tgt))
            self._adj_reverse.setdefault(tgt, []).append((rel, src))

        logger.info(
            "ImpactEngine loaded %d nodes, %d links",
            len(self._nodes_by_id),
            len(raw.get("links", [])),
        )

    @property
    def is_loaded(self) -> bool:
        return self.graph is not None

    # ── core analysis ────────────────────────────────────────

    def _collect_seed_nodes(self, changed_files: list[str]) -> tuple[set[str], list[str]]:
        """Collect seed node IDs and affected function names from changed files."""
        seed_ids: set[str] = set()
        affected_functions: list[str] = []
        for cf in changed_files:
            norm = cf.replace("\\", "/")
            if norm in self._nodes_by_file:
                self._add_seed_from_file(norm, seed_ids, affected_functions)
            else:
                self._add_seed_by_suffix(norm, seed_ids, affected_functions)
        return seed_ids, affected_functions

    def _add_seed_from_file(self, norm: str, seed_ids: set, affected: list) -> None:
        """Add seed nodes by exact file match."""
        for nid in self._nodes_by_file[norm]:
            seed_ids.add(nid)
            node = self._nodes_by_id.get(nid, {})
            label = node.get("label", "")
            if label and label not in affected:
                affected.append(label)

    def _add_seed_by_suffix(self, norm: str, seed_ids: set, affected: list) -> None:
        """Add seed nodes by suffix/basename match (fallback)."""
        for file_key, node_ids in self._nodes_by_file.items():
            if file_key.endswith("/" + norm) or file_key == norm.split("/")[-1]:
                seed_ids.update(node_ids)
                for nid in node_ids:
                    node = self._nodes_by_id.get(nid, {})
                    label = node.get("label", "")
                    if label and label not in affected:
                        affected.append(label)

    def _collect_blast_radius(self, seed_ids: set[str]) -> list[str]:
        """BFS outward from seeds to find dependent nodes (blast radius)."""
        blast_ids = self._bfs_forward(seed_ids, max_depth=3)
        blast_ids -= seed_ids
        blast_radius: list[str] = []
        for bid in blast_ids:
            node = self._nodes_by_id.get(bid, {})
            sf = node.get("source_file", "")
            label = node.get("label", "")
            entry = f"{sf}::{label}" if sf else label
            if entry and entry not in blast_radius:
                blast_radius.append(entry)
        return blast_radius

    def _collect_impacted_tests(self, blast_ids: set, seed_ids: set) -> list[str]:
        """Find test nodes in blast radius or reaching seeds via reverse BFS."""
        impacted_test_ids = blast_ids & self._test_node_ids
        for tnid in self._test_node_ids:
            reachable = self._bfs_reverse({tnid}, max_depth=3)
            if reachable & seed_ids:
                impacted_test_ids.add(tnid)
        impacted_tests: list[str] = []
        for tid in impacted_test_ids:
            node = self._nodes_by_id.get(tid, {})
            sf = node.get("source_file", "")
            if sf and sf not in impacted_tests:
                impacted_tests.append(sf)
        return impacted_tests

    @staticmethod
    def _recommendation(risk_score: float, impacted_test_count: int) -> str:
        """Map risk score to test recommendation."""
        if risk_score > 0.7 or impacted_test_count == 0:
            return "run-all"
        return "run-impacted" if impacted_test_count <= 10 else "run-all"

    def analyze(self, changed_files: list[str]) -> ImpactResult:
        """Compute blast radius and impacted tests from changed files."""
        if not changed_files:
            return ImpactResult(changed_file="", test_recommendation="skip")

        if not self.is_loaded:
            return ImpactResult(
                changed_file=changed_files[0] if len(changed_files) == 1 else "multiple",
                affected_functions=[], blast_radius=[], impacted_tests=[],
                risk_score=0.8, test_recommendation="run-all",
            )

        seed_ids, affected_functions = self._collect_seed_nodes(changed_files)
        if not seed_ids:
            return ImpactResult(
                changed_file=changed_files[0],
                affected_functions=[], blast_radius=[], impacted_tests=[],
                risk_score=0.1, test_recommendation="skip",
            )

        blast_ids = self._bfs_forward(seed_ids, max_depth=3)
        blast_radius = self._collect_blast_radius(seed_ids)
        impacted_tests = self._collect_impacted_tests(blast_ids, seed_ids)
        risk_score = self._compute_risk(
            seed_count=len(seed_ids),
            blast_count=len(blast_ids) - len(seed_ids),
            test_count=len(impacted_tests),
        )

        return ImpactResult(
            changed_file=changed_files[0] if len(changed_files) == 1 else "multiple",
            affected_functions=affected_functions,
            blast_radius=blast_radius,
            impacted_tests=impacted_tests,
            risk_score=risk_score,
            test_recommendation=self._recommendation(risk_score, len(impacted_tests)),
        )

    def recommend_tests(self, changed_files: list[str]) -> list[str]:
        """Return list of test files that should run.

        Returns an empty list to signal "run all tests" (high risk).
        """
        result = self.analyze(changed_files)
        if result.risk_score > 0.7 or result.test_recommendation == "run-all":
            return []
        return result.impacted_tests

    def what_breaks(self, function_name: str) -> list[str]:
        """Query: 'if I change X, what could break?'

        Returns list of "source_file::label" entries that depend on function_name.
        """
        if not self.is_loaded:
            return []

        # Find the node(s) matching the function name
        seed_ids: set[str] = set()
        for nid, node in self._nodes_by_id.items():
            label = node.get("label", "")
            norm_label = node.get("norm_label", "")
            if function_name.lower() in label.lower() or function_name.lower() in norm_label.lower():
                seed_ids.add(nid)

        if not seed_ids:
            return []

        blast_ids = self._bfs_forward(seed_ids, max_depth=3)
        blast_ids -= seed_ids

        result: list[str] = []
        for bid in blast_ids:
            node = self._nodes_by_id.get(bid, {})
            sf = node.get("source_file", "")
            label = node.get("label", "")
            entry = f"{sf}::{label}" if sf else label
            if entry and entry not in result:
                result.append(entry)
        return result

    def what_tests(self, file_path: str) -> list[str]:
        """Query: 'what tests cover this file?'"""
        result = self.analyze([file_path])
        return result.impacted_tests

    # ── internal helpers ─────────────────────────────────────

    def _bfs_forward(self, seeds: set[str], max_depth: int = 3) -> set[str]:
        """BFS along forward edges (outgoing)."""
        visited: set[str] = set(seeds)
        queue: deque[tuple[str, int]] = deque((s, 0) for s in seeds)

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for rel, neighbor in self._adj_forward.get(current, []):
                if rel not in _TRANSITIVE_RELATIONS:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return visited

    def _bfs_reverse(self, seeds: set[str], max_depth: int = 3) -> set[str]:
        """BFS along reverse edges (who points to me)."""
        visited: set[str] = set(seeds)
        queue: deque[tuple[str, int]] = deque((s, 0) for s in seeds)

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for rel, neighbor in self._adj_reverse.get(current, []):
                if rel not in _TRANSITIVE_RELATIONS:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return visited

    @staticmethod
    def _compute_risk(seed_count: int, blast_count: int, test_count: int) -> float:
        """Compute composite risk score 0.0–1.0.

        Factors:
          - Blast radius size (log-scaled)
          - Number of impacted tests
          - Number of directly changed symbols
        """
        blast_factor = min(blast_count / 50.0, 1.0)  # saturates at 50+ dependents
        test_factor = min(test_count / 20.0, 1.0)    # saturates at 20+ tests
        seed_factor = min(seed_count / 10.0, 1.0)    # saturates at 10+ changed symbols

        # Weighted composite
        raw = blast_factor * 0.5 + test_factor * 0.3 + seed_factor * 0.2
        return round(min(raw, 1.0), 3)


# ── CLI (standalone, for quick debugging) ─────────────────────

def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(description="KG‑driven impact analysis")
    p.add_argument("action", choices=["analyze", "what-breaks", "what-tests"], help="Action")
    p.add_argument("target", nargs="+", help="File(s) or function name")
    args = p.parse_args()

    engine = ImpactEngine()

    if args.action == "analyze":
        result = engine.analyze(args.target)
        print(f"Changed:        {result.changed_file}")
        print(f"Affected funcs: {len(result.affected_functions)}")
        print(f"Blast radius:   {len(result.blast_radius)}")
        print(f"Impacted tests: {len(result.impacted_tests)}")
        print(f"Risk score:     {result.risk_score}")
        print(f"Recommendation: {result.test_recommendation}")
        if result.impacted_tests:
            print("\nImpacted tests:")
            for t in result.impacted_tests:
                print(f"  - {t}")
    elif args.action == "what-breaks":
        broken = engine.what_breaks(args.target[0])
        print(f"Changing '{args.target[0]}' could break:")
        for b in broken[:20]:
            print(f"  - {b}")
        if len(broken) > 20:
            print(f"  ... and {len(broken) - 20} more")
    elif args.action == "what-tests":
        tests = engine.what_tests(args.target[0])
        print(f"Tests covering '{args.target[0]}':")
        for t in tests:
            print(f"  - {t}")


if __name__ == "__main__":
    _cli()
