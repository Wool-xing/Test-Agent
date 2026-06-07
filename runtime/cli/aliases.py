"""Command aliases — user-defined shortcuts for commands.

Persist to workspace/gateway/aliases.json.
Auto-expand when user types alias name (non-slash).
/alias add|list|remove for management.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Alias:
    name: str
    command: str
    description: str = ""


def _file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "aliases.json"


def _load() -> list[dict]:
    p = _file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(aliases: list[dict]) -> None:
    _file().write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")


def list_aliases() -> list[Alias]:
    return [Alias(**a) for a in _load()]


def add_alias(name: str, command: str, description: str = "") -> Alias:
    a = Alias(name=name, command=command, description=description)
    aliases = _load()
    # Replace if exists
    for i, existing in enumerate(aliases):
        if existing.get("name") == name:
            aliases[i] = asdict(a)
            _save(aliases)
            return a
    aliases.append(asdict(a))
    _save(aliases)
    return a


def remove_alias(name: str) -> bool:
    aliases = _load()
    for i, a in enumerate(aliases):
        if a.get("name") == name:
            aliases.pop(i)
            _save(aliases)
            return True
    return False


def expand_alias(text: str) -> str | None:
    """Check if text matches an alias name. Returns expanded command or None."""
    for a in _load():
        if a.get("name") == text.strip():
            return a.get("command", "")
    return None


def get_alias(name: str) -> Alias | None:
    for a in _load():
        if a.get("name") == name:
            return Alias(**a)
    return None
