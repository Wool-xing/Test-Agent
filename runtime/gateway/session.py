"""Cross-platform session continuity.

Stores conversation handles keyed by (user, app_session); each platform may attach
its native chat_id so a user moving Telegram → Slack still finds the same context.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.config.settings import get_settings


def _store_path() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "sessions.json"


def _load() -> dict[str, Any]:
    p = _store_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(state: dict) -> None:
    p = _store_path()
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def bind(user: str, session_id: str, platform: str, native_id: str) -> None:
    """Attach platform-native chat id to a logical session."""
    state = _load()
    sess = state.setdefault(session_id, {"user": user, "platforms": {}, "created_at": datetime.now(timezone.utc).isoformat()})
    sess["platforms"][platform] = native_id
    sess["last_active"] = datetime.now(timezone.utc).isoformat()
    _save(state)


def lookup(session_id: str) -> dict | None:
    return _load().get(session_id)


def find_by_user(user: str) -> list[dict]:
    return [{"session_id": sid, **info} for sid, info in _load().items() if info.get("user") == user]


def native_id_for(session_id: str, platform: str) -> str | None:
    sess = lookup(session_id)
    return None if sess is None else sess.get("platforms", {}).get(platform)
