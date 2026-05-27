"""AST‑based test impact analysis — find which tests to run for a given change set.

Standalone module. Does NOT modify regression_scope.py.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


class ImportGraph:
    """Lightweight import dependency graph built from AST parsing."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._imports: dict[str, set[str]] = {}   # module → {modules it imports}
        self._imported_by: dict[str, set[str]] = {}  # module → {modules that import it}

    def scan(self, max_files: int = 500) -> int:
        """Scan all .py files under root, build bidirectional import graph."""
        count = 0
        for f in self.root.rglob("*.py"):
            if count >= max_files:
                break
            if ".venv" in f.parts or "__pycache__" in f.parts or "node_modules" in f.parts:
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            module = _path_to_module(f, self.root)
            self._imports.setdefault(module, set())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported = alias.name.split(".")[0]
                        self._imports[module].add(imported)
                        self._imported_by.setdefault(imported, set()).add(module)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported = node.module.split(".")[0]
                    self._imports[module].add(imported)
                    self._imported_by.setdefault(imported, set()).add(module)
            count += 1
        return count

    def affected_modules(self, changed_files: list[str]) -> set[str]:
        """Given a list of changed file paths, return all modules potentially affected.

        Includes:
          - The changed modules themselves
          - Any module that imports them (1‑hop downstream)
        """
        changed_modules: set[str] = set()
        for cf in changed_files:
            m = _path_to_module(Path(cf), self.root)
            if m:
                changed_modules.add(m)

        affected: set[str] = set(changed_modules)
        for m in changed_modules:
            downstream = self._imported_by.get(m, set())
            affected.update(downstream)

        return affected

    def affected_tests(self, changed_files: list[str], test_dirs: list[str] | None = None) -> list[str]:
        """Find test files most likely impacted by changed_files.

        Returns sorted list of test file paths.
        """
        if test_dirs is None:
            test_dirs = ["tests", "runtime/tests"]

        affected = self.affected_modules(changed_files)

        # Find test files that import affected modules or are in test dirs
        candidates: list[str] = []
        for f in self.root.rglob("test_*.py"):
            if ".venv" in f.parts or "__pycache__" in f.parts:
                continue
            try:
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in affected:
                            candidates.append(str(f.relative_to(self.root)))
                            break
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in affected:
                    candidates.append(str(f.relative_to(self.root)))
                    break

        # Also include any test_*.py in test directories
        for td in test_dirs:
            td_path = self.root / td
            if td_path.is_dir():
                for tf in td_path.rglob("test_*.py"):
                    rel = str(tf.relative_to(self.root))
                    if rel not in candidates:
                        candidates.append(rel)

        return sorted(set(candidates))


def _path_to_module(p: Path, root: Path) -> str:
    """Convert a file path to a Python module name relative to root."""
    try:
        rel = p.relative_to(root)
    except ValueError:
        return p.stem
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def analyze_impact(
    project_root: str | Path,
    base_branch: str = "main",
    test_dirs: list[str] | None = None,
) -> dict:
    """Main entry point: git diff → import graph → impacted test list.

    Returns:
        {
            "changed_files": [...],
            "changed_modules": [...],
            "affected_modules": [...],
            "impacted_tests": [...],
            "impacted_count": int,
            "recommendation": "targeted" | "full" | "none",
        }
    """
    root = Path(project_root)
    if not root.is_dir():
        raise FileNotFoundError(f"project root not found: {root}")

    # git diff
    changed_files: list[str] = []
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", f"{base_branch}...HEAD"],
            capture_output=True, text=True, check=False,
        )
        changed_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception as e:
        raise RuntimeError(f"git diff failed: {e}") from e

    if not changed_files:
        return {
            "changed_files": [],
            "changed_modules": [],
            "affected_modules": [],
            "impacted_tests": [],
            "impacted_count": 0,
            "recommendation": "none",
        }

    # Build import graph
    graph = ImportGraph(root)
    scanned = graph.scan()
    changed_modules = list({_path_to_module(Path(f), root) for f in changed_files})
    affected_modules = sorted(graph.affected_modules(changed_files))
    impacted_tests = graph.affected_tests(changed_files, test_dirs)

    # Recommendation
    if len(impacted_tests) == 0:
        rec = "none"
    elif len(impacted_tests) <= 10:
        rec = "targeted"
    else:
        rec = "full"

    return {
        "changed_files": changed_files,
        "changed_modules": changed_modules,
        "affected_modules": affected_modules,
        "impacted_tests": impacted_tests,
        "impacted_count": len(impacted_tests),
        "modules_scanned": scanned,
        "recommendation": rec,
    }


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    import json as _json

    p = argparse.ArgumentParser(description="AST‑based test impact analysis")
    p.add_argument("root", nargs="?", default=".", help="project root directory")
    p.add_argument("--base", default="main", help="base branch for git diff")
    p.add_argument("--json", action="store_true", help="output JSON")
    args = p.parse_args()

    report = analyze_impact(Path(args.root), base_branch=args.base)

    if args.json:
        print(_json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Changed files:   {len(report['changed_files'])}")
        print(f"Changed modules: {len(report['changed_modules'])}")
        print(f"Affected:        {len(report['affected_modules'])}")
        print(f"Impacted tests:  {report['impacted_count']}")
        print(f"Recommendation:  {report['recommendation']}")
        if report["impacted_tests"]:
            print("\nImpacted tests:")
            for t in report["impacted_tests"]:
                print(f"  • {t}")


if __name__ == "__main__":
    _cli()
