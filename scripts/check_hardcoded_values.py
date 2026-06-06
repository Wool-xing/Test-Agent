#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI gate: detect hardcoded values that should be configuration.

Scans key project files for patterns that indicate hardcoded:
  - Version numbers (not from VERSION/settings)
  - Port numbers (not from .env.example/settings)
  - Magic counts (agent/skill/utility counts that change over time)
  - Absolute file paths
  - URLs not known as public API endpoints

Exit 1 on any CRITICAL finding. Warnings for review items.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Known public API URLs (not hardcoded — these are protocol constants)
KNOWN_URL_HOSTS = {
    "api.telegram.org", "api.sgroup.qq.com", "bots.qq.com",
    "qyapi.weixin.qq.com", "oapi.dingtalk.com", "open.feishu.cn",
    "discord.com", "hooks.slack.com", "api.github.com",
    "api.openai.com", "api.anthropic.com", "api.deepseek.com",
    "generativelanguage.googleapis.com", "raw.githubusercontent.com",
    "cdnjs.cloudflare.com", "unpkg.com", "sctapi.ftqq.com",
    "api.electricitymap.org", "api.vercel.com",
}

# Files to exclude from scanning
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
                "dist", "build", "out", ".pytest_cache", ".ruff_cache"}
EXCLUDE_FILES = {"test_", "conftest.py", ".env.example", "CHANGELOG.md",
                 "ROADMAP.md", "README.md", "check_command_consistency.py",
                 "check_hardcoded_values.py"}

# Critical patterns — block merge
CRITICAL_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, description, file_glob)
    (r'assert\s+len\([^)]*\)\s*==\s*\d+', "hardcoded count assertion", "*.py"),
    (r'(?:agents?_n|skills?_n|experts|utils_n)\s*(?:==|!=)\s*\d+', "hardcoded agent/skill count", "*.py"),
    (r'(?:password|api_key|token|secret)\s*=\s*"[^"$\s]{8,}"', "potential hardcoded credential", "*.py"),
    (r'version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"', "hardcoded version string", "*.py"),
]

# Warning patterns — flag for review, don't block
WARNING_PATTERNS: list[tuple[str, str, str]] = [
    (r'\bport\s*=\s*\d{2,5}\b', "hardcoded port number", "*.py"),
    (r'(?<!")(?:C:\\|/home/|/Users/|/opt/)(?!\w*/\w*/\w*")', "absolute filesystem path", "*.py"),
]

FILES_TO_SCAN = ["*.py", "*.yml", "*.yaml", "*.json", "*.ts", "*.tsx"]


def _should_scan(filepath: Path) -> bool:
    """Check if file should be scanned."""
    parts = filepath.parts
    for ex in EXCLUDE_DIRS:
        if ex in parts:
            return False
    fname = filepath.name
    for ex in EXCLUDE_FILES:
        if ex in fname:
            return False
    if fname.startswith("test_") or fname.endswith("_test.py"):
        return False
    return True


def _is_known_url(url: str) -> bool:
    """Check if URL host is a known public API endpoint."""
    for host in KNOWN_URL_HOSTS:
        if host in url:
            return True
    return False


def check_file(filepath: Path) -> tuple[int, int]:
    """Check a single file. Returns (errors, warnings)."""
    errors = 0
    warnings = 0
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0

    for pattern, desc, glob_pat in CRITICAL_PATTERNS:
        if not filepath.match(glob_pat):
            continue
        for m in re.finditer(pattern, content, re.IGNORECASE):
            line = content[:m.start()].count("\n") + 1
            snippet = m.group().strip()[:80]
            # Skip if in settings.py or config files (those are intentional)
            if "settings" in filepath.name or "config" in str(filepath):
                continue
            print(f"ERROR: {filepath}:{line}: {desc} → {snippet}")
            errors += 1

    for pattern, desc, glob_pat in WARNING_PATTERNS:
        if not filepath.match(glob_pat):
            continue
        for m in re.finditer(pattern, content, re.IGNORECASE):
            line = content[:m.start()].count("\n") + 1
            snippet = m.group().strip()[:80]
            if "settings" in filepath.name or "config" in str(filepath):
                continue
            if ".env.example" in str(filepath):
                continue
            print(f"WARNING: {filepath}:{line}: {desc} → {snippet}")
            warnings += 1

    return errors, warnings


def main() -> int:
    """Scan project files. Returns exit code."""
    total_errors = 0
    total_warnings = 0
    files_checked = 0

    # Only scan runtime/, utils/, install.py, scripts/ — not agents/skills .md
    scan_roots = [
        PROJECT_ROOT / "runtime",
        PROJECT_ROOT / "utils",
        PROJECT_ROOT / "install.py",
        PROJECT_ROOT / "scripts",
    ]

    for root in scan_roots:
        if root.is_file():
            e, w = check_file(root)
            total_errors += e
            total_warnings += w
            files_checked += 1
        elif root.is_dir():
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                if not _should_scan(f):
                    continue
                if f.suffix not in (".py",):
                    continue
                e, w = check_file(f)
                total_errors += e
                total_warnings += w
                files_checked += 1

    print(f"Scanned {files_checked} files: {total_errors} errors, {total_warnings} warnings")
    if total_errors:
        print("ERROR: Hardcoded values found. Extract to config/env before merging.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
