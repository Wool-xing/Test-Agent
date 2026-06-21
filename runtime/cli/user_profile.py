"""User profile — auto-learn preferences + trusted commands (P3 #20-21).

Persists to MEMORY.md with a structured prefix so the knowledge is both
human-readable and machine-parseable across sessions.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from runtime.config.settings import get_settings

_PROFILE_PREFIX = "[profile]"
_TRUST_PREFIX = "[trust]"

_MEMORY_PATH = get_settings().gateway_dir / "MEMORY.md"


def _read_profile_entries() -> dict[str, str]:
    """Parse MEMORY.md for profile entries."""
    if not _MEMORY_PATH.is_file():
        return {}
    entries: dict[str, str] = {}
    try:
        for line in _MEMORY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"- {_PROFILE_PREFIX} "):
                parts = line[len(f"- {_PROFILE_PREFIX} "):].split("=", 1)
                if len(parts) == 2:
                    entries[parts[0].strip()] = parts[1].strip()
    except OSError:
        pass
    return entries


def _read_trusted_commands() -> set[str]:
    """Parse MEMORY.md for trusted command entries."""
    if not _MEMORY_PATH.is_file():
        return set()
    trusted: set[str] = set()
    try:
        for line in _MEMORY_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"- {_TRUST_PREFIX} "):
                cmd = line[len(f"- {_TRUST_PREFIX} "):].strip()
                if cmd:
                    trusted.add(cmd)
    except OSError:
        pass
    return trusted


def get_preference(key: str, default: str = "") -> str:
    """Read a user preference. Auto-learned from usage."""
    return _read_profile_entries().get(key, default)


def set_preference(key: str, value: str) -> None:
    """Store a user preference (auto-learned or explicit)."""
    from runtime.cli.conversation import save_memory_fact
    save_memory_fact(f"{_PROFILE_PREFIX} {key}={value}")


def learn_from_usage() -> dict[str, str]:
    """Auto-learn preferences based on current environment."""
    prefs: dict[str, str] = {}

    provider = os.environ.get("TAGENT_LLM_PROVIDER", "")
    if provider:
        prefs["provider"] = provider

    model = os.environ.get("TAGENT_LLM_MODEL", "")
    if model:
        prefs["model"] = model

    lang = os.environ.get("TAGENT_LANG", "zh")
    prefs["lang"] = lang

    # Persist learned preferences
    for k, v in prefs.items():
        set_preference(k, v)

    return prefs


def is_trusted(command: str) -> bool:
    """Check if a command has been trusted by the user."""
    # Built-in safe commands are always trusted
    always_trusted = {"help", "status", "tools", "ls", "model", "cost", "sessions"}
    if command in always_trusted:
        return True
    return command in _read_trusted_commands()


def trust_command(command: str) -> None:
    """Mark a command as trusted (user approved it)."""
    from runtime.cli.conversation import save_memory_fact
    save_memory_fact(f"{_TRUST_PREFIX} {command}")
