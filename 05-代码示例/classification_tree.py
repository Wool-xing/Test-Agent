# SPDX-License-Identifier: MIT
"""
Classification Tree Method (CTM) — ISTQB advanced test design technique.

Generates test combinations from orthogonal classification dimensions.
Reduces combinatorial explosion via pairwise coverage.
"""

from __future__ import annotations

import itertools
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class Classification:
    name: str
    classes: List[str]  # mutually exclusive classes within this classification


@dataclass
class TreeModel:
    classifications: List[Classification] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)  # "A.class1 != B.class2" etc.

    def add(self, name: str, classes: List[str]) -> Classification:
        c = Classification(name=name, classes=classes)
        self.classifications.append(c)
        return c

    def combinations(self) -> List[Dict[str, str]]:
        """Generate all combinations of classes across classifications."""
        if not self.classifications:
            return []
        names = [c.name for c in self.classifications]
        values = [c.classes for c in self.classifications]
        result = []
        for combo in itertools.product(*values):
            entry = dict(zip(names, combo))
            if self._satisfies_constraints(entry):
                result.append(entry)
        return result

    def pairwise(self) -> List[Dict[str, str]]:
        """Generate pairwise (2‑way) coverage subset.
        Falls back to full combinations if < 3 classifications or pairwise tool unavailable.
        """
        all_combos = self.combinations()
        if len(self.classifications) <= 2:
            return all_combos
        if len(self.classifications) == 3:
            return self._pairwise_3way()
        try:
            from allpairspy import AllPairs
            names = [c.name for c in self.classifications]
            values = [c.classes for c in self.classifications]
            pairs = []
            for combo in AllPairs(values):
                entry = dict(zip(names, combo))
                if self._satisfies_constraints(entry):
                    pairs.append(entry)
            return pairs
        except ImportError:
            logger.info("allpairspy not installed — falling back to full combinations")
            return all_combos

    def _pairwise_3way(self) -> List[Dict[str, str]]:
        """Simple 3‑way pairwise: cover all pairs of first 2 dims, repeat for last."""
        names = [c.name for c in self.classifications]
        pairs: set[tuple] = set()
        result: List[Dict[str, str]] = []
        for i in range(len(self.classifications)):
            for j in range(i + 1, len(self.classifications)):
                for ci in self.classifications[i].classes:
                    for cj in self.classifications[j].classes:
                        entry = {names[i]: ci, names[j]: cj}
                        for k, c in enumerate(self.classifications):
                            if k not in (i, j):
                                entry[names[k]] = c.classes[0]
                        key = tuple(entry[n] for n in names)
                        if key not in pairs and self._satisfies_constraints(entry):
                            pairs.add(key)
                            result.append(entry)
        return result

    def _satisfies_constraints(self, entry: Dict[str, str]) -> bool:
        for constraint in self.constraints:
            # Simple: "Browser.Firefox != OS.Linux" format
            parts = constraint.split()
            if len(parts) == 3:
                left, op, right = parts
                l_dim, l_val = left.split(".")
                r_dim, r_val = right.split(".")
                l_actual = entry.get(l_dim)
                r_actual = entry.get(r_dim)
                if l_actual and r_actual:
                    if op == "!=" and l_actual == l_val and r_actual == r_val:
                        return False
                    if op == "==" and not (l_actual == l_val and r_actual == r_val):
                        return False
        return True

    def to_dict(self) -> Dict:
        return {
            "classifications": [{"name": c.name, "classes": c.classes} for c in self.classifications],
            "constraints": self.constraints,
            "combinations_count": len(self.combinations()),
            "pairwise_count": len(self.pairwise()),
        }

    def to_markdown(self) -> str:
        """Generate markdown table of test combinations."""
        combos = self.pairwise() or self.combinations()
        if not combos:
            return "*Empty classification tree*"
        headers = list(combos[0].keys())
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
        for c in combos:
            lines.append("| " + " | ".join(c[h] for h in headers) + " |")
        lines.append(f"\n*{len(combos)} pairwise combinations (from {len(self.combinations())} total)*")
        return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Classification Tree Method (ISTQB)")
    p.add_argument("--load", help="Load tree from JSON file")
    p.add_argument("--pairwise", action="store_true", default=True, help="Use pairwise (default)")
    p.add_argument("--full", action="store_true", help="Output all combinations")
    p.add_argument("--markdown", action="store_true", help="Output markdown table")
    args = p.parse_args()

    if args.load:
        data = json.loads(Path(args.load).read_text(encoding="utf-8"))
        tree = TreeModel(constraints=data.get("constraints", []))
        for c in data["classifications"]:
            tree.add(c["name"], c["classes"])
    else:
        # Demo: login page classification tree
        tree = TreeModel()
        tree.add("Browser", ["Chrome", "Firefox", "Safari", "Edge"])
        tree.add("OS", ["Windows", "macOS", "Linux", "iOS", "Android"])
        tree.add("Auth Method", ["Password", "SMS", "OAuth", "Passkey"])
        tree.add("Network", ["4G", "5G", "WiFi", "Offline"])
        tree.constraints = ["Browser.Safari != OS.Linux", "Browser.Safari != OS.Android"]

    if args.markdown:
        print(tree.to_markdown())
    else:
        combos = tree.combinations() if args.full else tree.pairwise()
        print(json.dumps(tree.to_dict(), indent=2, ensure_ascii=False))
        if not args.full:
            print(f"\n--- {len(combos)} pairwise combinations ---")
            for i, combo in enumerate(combos, 1):
                print(f"  {i:3d}. " + " | ".join(f"{k}={v}" for k, v in combo.items()))


if __name__ == "__main__":
    _cli()
