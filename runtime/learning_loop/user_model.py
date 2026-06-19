"""Dialectic user modeling (inspired by Honcho).

Cross-session profile of user preferences / vocabulary / working style.
Stored as JSON facts under `workspace/learning/user_models/{user_id}.json`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.config.settings import get_settings


def _user_dir() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning" / "user_models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(user_id: str) -> Path:
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_.") or "anonymous"
    return _user_dir() / f"{safe}.json"


def load(user_id: str) -> dict:
    p = _path(user_id)
    if not p.is_file():
        return {"user_id": user_id, "facts": [], "created_at": datetime.now(timezone.utc).isoformat()}
    return json.loads(p.read_text(encoding="utf-8"))


def add_fact(user_id: str, key: str, value: Any, *, source: str | None = None, confidence: float = 0.8) -> None:
    model = load(user_id)
    model.setdefault("facts", []).append(
        {
            "key": key,
            "value": value,
            "source": source,
            "confidence": confidence,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )
    _path(user_id).write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")


def get_facts(user_id: str, key: str | None = None) -> list[dict]:
    facts = load(user_id).get("facts", [])
    return [f for f in facts if key is None or f["key"] == key]


def remove_fact(user_id: str, *, key: str, value: Any | None = None) -> int:
    """Remove matching facts. Returns count removed."""
    model = load(user_id)
    before = len(model.get("facts", []))
    model["facts"] = [f for f in model.get("facts", []) if not (f["key"] == key and (value is None or f["value"] == value))]
    _path(user_id).write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    return before - len(model["facts"])
