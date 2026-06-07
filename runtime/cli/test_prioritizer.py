"""Test prioritization — run tests for changed modules first.

Analyzes git diff to determine which source files changed,
maps them to test modules, and prioritizes test execution order.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Map source paths to test modules (regex patterns)
SOURCE_TO_TEST: list[tuple[str, str]] = [
    (r"runtime/api/", "API endpoints"),
    (r"runtime/router/", "LLM routing"),
    (r"runtime/orchestrator/", "DAG execution"),
    (r"runtime/backends/", "Terminal backends"),
    (r"runtime/gateway/", "IM gateway"),
    (r"runtime/cli/", "CLI / REPL"),
    (r"runtime/mcp/", "MCP servers"),
    (r"runtime/scheduler/", "Cron scheduler"),
    (r"utils/testing/", "Testing utilities"),
    (r"utils/security/", "Security tools"),
    (r"utils/performance/", "Performance tools"),
    (r"utils/protocols/", "Protocol adapters"),
    (r"utils/platforms/", "Platform drivers"),
    (r"utils/reporting/", "Report generation"),
    (r"utils/design/", "Test design"),
    (r"utils/data/", "Test data"),
    (r"utils/trackers/", "Bug trackers"),
    (r"desktop/", "Desktop app"),
    (r"runtime/web/", "Web UI"),
    (r"ai/agents/", "Agent definitions"),
    (r"ai/skills/", "Skill definitions"),
    (r"deploy/config/", "Configuration"),
    (r"install.py", "Installation"),
]


def get_changed_files(since: str = "HEAD~1") -> list[str]:
    """Get list of changed files from git."""
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", since],
            capture_output=True, text=True, timeout=10,
            cwd=Path.cwd(),
        )
        if r.returncode == 0:
            return [f for f in r.stdout.strip().split("\n") if f]
    except Exception:
        pass
    return []


def _match_module(filepath: str) -> str | None:
    """Match a changed file to a test module. Returns module name or None."""
    import re
    for pattern, module in SOURCE_TO_TEST:
        if re.search(pattern, filepath):
            return module
    return None


def prioritize(extra_files: list[str] | None = None) -> dict[str, Any]:
    """Analyze changes and return prioritized test order.

    Returns: {changed_modules, priority_order, all_modules, change_count}
    """
    changed = get_changed_files()
    if extra_files:
        changed.extend(extra_files)

    modules: dict[str, int] = {}
    for f in changed:
        m = _match_module(f)
        if m:
            modules[m] = modules.get(m, 0) + 1

    # Sort by change count (most changed first)
    priority = sorted(modules.items(), key=lambda x: x[1], reverse=True)
    all_known = [m for _, m in SOURCE_TO_TEST]

    return {
        "changed_files": len(changed),
        "changed_modules": [name for name, _ in priority],
        "priority_detail": priority,
        "all_modules": all_known,
    }
