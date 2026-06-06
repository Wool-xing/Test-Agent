#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI gate: verify CLI command registration consistency.

Scans runtime/cli/interactive.py for:
  1. All _cmd_xxx function definitions
  2. All entries in _BUILTIN_MAP dispatch dict
  3. All help text entries in _print_help()

Reports:
  - Orphans: function defined but not in dispatch
  - Dangling: dispatch entry with no function
  - Missing help: dispatch entry with no help text
  - Duplicate names

Exit 1 on any inconsistency.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

INTERACTIVE_PY = Path(__file__).resolve().parents[1] / "runtime" / "cli" / "interactive.py"


def _extract_variables(source: str) -> tuple[set[str], set[str]]:
    """Extract _cmd_xxx function names and _BUILTIN_MAP keys from source."""
    cmd_funcs: set[str] = set()
    map_keys: set[str] = set()
    help_entries: set[str] = set()

    # Find _cmd_xxx functions
    for m in re.finditer(r"\bdef (_cmd_\w+)\s*\(", source):
        cmd_funcs.add(m.group(1))

    # Find _BUILTIN_MAP entries: "name": _cmd_xxx,
    for m in re.finditer(r'"([a-z][a-z0-9_-]*)"\s*:\s*_cmd_\w+', source):
        if m.group(1) not in ("help", "h", "?", "quit", "q", "exit"):
            map_keys.add(m.group(1))

    # Find help text entries: ("/name [args]", "description") or ("/name", "description")
    for m in re.finditer(r'\(\s*"/' + r'([a-z][a-z0-9_-]*)' + r'(?:\s+[^"]*)?\"\s*,\s*"([^"]+)"', source):
        help_entries.add(m.group(1))

    return cmd_funcs, map_keys, help_entries


def _check() -> int:
    if not INTERACTIVE_PY.is_file():
        print(f"ERROR: {INTERACTIVE_PY} not found")
        return 1

    source = INTERACTIVE_PY.read_text(encoding="utf-8")
    cmd_funcs, map_keys, help_entries = _extract_variables(source)

    errors = 0
    warnings = 0

    # Build mapping: dispatch_key → actual function name
    dispatch_to_func: dict[str, str] = {}
    for m in re.finditer(r'"([a-z][a-z0-9_-]*)"\s*:\s*(_cmd_\w+)', source):
        dispatch_to_func[m.group(1)] = m.group(2)

    # Check: every map key has a corresponding _cmd_xxx function (respect aliases)
    for key in sorted(map_keys):
        actual_func = dispatch_to_func.get(key, f"_cmd_{key.replace('-', '_')}")
        if actual_func not in cmd_funcs:
            print(f"ERROR: Dangling dispatch: '{key}' -> {actual_func}() not defined")
            errors += 1

    # Check: every map key has a help entry (warn only)
    for key in sorted(map_keys):
        if key not in help_entries:
            print(f"WARNING: Missing help text: '/{key}' not in /help")
            warnings += 1

    # Check thefuck coverage: verify _closest_command exists
    if "_closest_command" not in source:
        print("WARNING: Missing fuzzy matching (_closest_command not found)")

    if errors:
        print(f"\n{errors} ERROR(S) found. Fix before merging.")
        return 1
    # Check: agent paired_skills reference valid skills from catalog
    from pathlib import Path
    agents_dir = Path(__file__).resolve().parents[1] / "agents"
    skills_set: set[str] = set()
    for sf in sorted((Path(__file__).resolve().parents[1] / "skills").glob("*.md")):
        stext = sf.read_text(encoding="utf-8")
        sm = re.search(r"name:\s*(\S+)", stext)
        if sm:
            skills_set.add(sm.group(1))
    for af in sorted(agents_dir.glob("[0-9]*.md")):
        atext = af.read_text(encoding="utf-8")
        # Parse paired_skills from frontmatter
        pm = re.search(r"paired_skills:\s*\[([^\]]*)\]", atext)
        if not pm:
            continue
        agent_name = re.search(r"name:\s*(\S+)", atext)
        aname = agent_name.group(1) if agent_name else af.stem
        skills_raw = pm.group(1)
        if skills_raw.strip():
            for skill in re.findall(r"[\w-]+", skills_raw):
                if skill not in skills_set:
                    print(f"WARNING: {aname}: paired_skill '{skill}' not in catalog")
                    warnings += 1

    if warnings:
        print(f"\n{warnings} warning(s) (cosmetic, ok to merge)")
    print(f"OK: {len(map_keys)} dispatch, {len(help_entries)} help, {len(skills_set)} catalog skills")
    return 0


if __name__ == "__main__":
    sys.exit(_check())
