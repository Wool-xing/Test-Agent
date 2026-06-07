"""Test data cleaner — remove temporary artifacts, preserve deliverables.

Cleans: temp files, logs, caches, stale test data, orphaned ZAP/Burp outputs.
Preserves: reports, test cases, test plans, scripts, baselines, configs.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).resolve().parents[2] / "workspace"

# Preserve: test deliverables (never cleaned)
PRESERVE_DIRS = {
    "测试报告", "测试用例", "测试计划", "测试数据",
    "需求分析", "自动化脚本", "_demo",
}
PRESERVE_FILES = {
    ".gitkeep", "README.md", "test_data.json", "perf_baseline.json",
    "regression_*.json", "flaky_tracker.json",
}

# Clean: temporary / generated artifacts
CLEAN_PATTERNS = {
    "*.log", "*.tmp", "*.cache", "*.lock",
    ".doctor_write_test", "hook_log.jsonl",
}


def _should_preserve(path: Path) -> bool:
    """Check if path is a deliverable that should be preserved."""
    parts = path.parts
    # Preserve files in PRESERVE_DIRS
    for part in parts:
        if part in PRESERVE_DIRS:
            return True
    # Preserve specific files
    for pat in PRESERVE_FILES:
        if path.match(pat):
            return True
    return False


def get_cleanable() -> list[dict[str, Any]]:
    """List files/dirs that can be cleaned. Returns [{path, size_kb, age_hours}]."""
    results = []
    if not WORKSPACE.is_dir():
        return results
    now = time.time()
    for item in WORKSPACE.rglob("*"):
        if not item.is_file():
            continue
        if _should_preserve(item):
            continue
        for pat in CLEAN_PATTERNS:
            if item.match(pat):
                size = item.stat().st_size
                age_h = (now - item.stat().st_mtime) / 3600
                results.append({
                    "path": str(item.relative_to(WORKSPACE)),
                    "size_kb": round(size / 1024, 1),
                    "age_hours": round(age_h, 1),
                })
                break
    return sorted(results, key=lambda x: x["size_kb"], reverse=True)


def run_cleanup(dry_run: bool = True) -> dict[str, Any]:
    """Clean temporary files. dry_run=True only lists without deleting.

    Returns: {cleaned_count, freed_kb, dry_run, files}
    """
    cleanable = get_cleanable()
    cleaned = 0
    freed = 0
    for item in cleanable:
        path = WORKSPACE / item["path"]
        if not dry_run and path.is_file():
            try:
                path.unlink()
                cleaned += 1
                freed += item["size_kb"]
            except OSError:
                pass
        elif dry_run:
            cleaned += 1
            freed += item["size_kb"]

    return {
        "cleaned_count": cleaned,
        "freed_kb": round(freed, 1),
        "dry_run": dry_run,
        "files": cleanable[:20],
    }
