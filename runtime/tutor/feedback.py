"""User feedback

Users flag wrong explanations → workspace/learning/feedback/{date}.jsonl
curator periodically reviews & downgrades card confidence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from runtime.config.settings import get_settings


def _feedback_dir() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning" / "feedback"
    d.mkdir(parents=True, exist_ok=True)
    return d


def flag_error(card_id: str, run_id: str, note: str = "", *, user: str | None = None) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    target = _feedback_dir() / f"{ts}.jsonl"
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "card_id": card_id,
        "run_id": run_id,
        "note": note,
        "user": user,
        "kind": "error_flag",
    }
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target


def list_flags(card_id: str | None = None, *, days: int = 30) -> list[dict]:
    """Return recent flags, optionally filtered by card_id."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for p in _feedback_dir().glob("*.jsonl"):
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if datetime.fromisoformat(rec["ts"]) < cutoff:
                        continue
                    if card_id and rec.get("card_id") != card_id:
                        continue
                    out.append(rec)
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
    return out
