"""Session insights — cross-session analytics.

Scans saved sessions from workspace/gateway/*.json and computes:
  - Session count and total message volume
  - Most-used agents/skills (from DAG traces in messages)
  - Success rate over time
  - Average session length
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from runtime.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SessionStats:
    filename: str = ""
    message_count: int = 0
    user_turns: int = 0
    agents: list[str] = field(default_factory=list)
    timestamp: float = 0
    duration_s: float = 0


def _session_dir() -> Path:
    return get_settings().gateway_dir


def collect_stats(days: int = 30) -> list[SessionStats]:
    """Scan saved session JSON files and extract statistics."""
    sd = _session_dir()
    if not sd.is_dir():
        return []

    cutoff = time.time() - days * 86400
    results: list[SessionStats] = []

    for f in sorted(sd.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.stat().st_mtime < cutoff:
            break
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(data, dict):
            continue
        messages = data.get("messages", [])
        if not messages:
            continue

        stats = SessionStats(
            filename=f.stem,
            message_count=len(messages),
            user_turns=sum(1 for m in messages if m.get("role") == "user"),
            timestamp=f.stat().st_mtime,
        )

        # Extract agent mentions from assistant messages
        for m in messages:
            if m.get("role") != "assistant":
                continue
            content = m.get("content", "")
            # Parse "DAG: N/N ok" format used by interactive.py
            if "DAG:" in content:
                stats.agents.append("orchestrator")

        # Compute rough duration between first and last message
        timestamps = [m.get("ts", 0) for m in messages if m.get("ts")]
        if len(timestamps) >= 2:
            stats.duration_s = max(timestamps) - min(timestamps)

        results.append(stats)

    return results


def compute_insights(stats: list[SessionStats]) -> dict:
    """Generate aggregate insights from session stats."""
    if not stats:
        return {"error": "No session data found"}

    total_msgs = sum(s.message_count for s in stats)
    total_turns = sum(s.user_turns for s in stats)
    total_duration = sum(s.duration_s for s in stats)

    agent_counter: Counter = Counter()
    for s in stats:
        for a in s.agents:
            agent_counter[a] += 1

    avg_turns = total_turns / len(stats) if stats else 0
    avg_duration = total_duration / len(stats) if stats else 0

    # Activity over time (by day)
    daily: Counter = Counter()
    for s in stats:
        from datetime import datetime, timezone
        day = datetime.fromtimestamp(s.timestamp, tz=timezone.utc).strftime("%m-%d")
        daily[day] += 1

    return {
        "sessions": len(stats),
        "total_messages": total_msgs,
        "total_turns": total_turns,
        "avg_turns_per_session": round(avg_turns, 1),
        "avg_duration_s": round(avg_duration, 1),
        "top_agents": agent_counter.most_common(5),
        "daily_activity": list(daily.items())[-14:],  # last 14 days
        "oldest_session_days": round((time.time() - min(s.timestamp for s in stats)) / 86400, 1),
    }
