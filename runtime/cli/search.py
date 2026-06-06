"""会话全文搜索 — SQLite FTS5.

Indexes conversation messages for full-text search across sessions.
Standalone SQLite database at workspace/gateway/search.db — no PostgreSQL dependency.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

_SEARCH_DB = Path(__file__).resolve().parents[2] / "workspace" / "gateway" / "search.db"
_lock = threading.Lock()


def _ensure_db() -> sqlite3.Connection:
    """Open (or create) the FTS5 database. Thread-safe."""
    _SEARCH_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_SEARCH_DB))
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
                 "  session_id, role, content, ts, tokenize='unicode61'"
                 ")")
    conn.commit()
    return conn


def index_message(session_id: str, role: str, content: str, ts: str | None = None) -> None:
    """Index a single conversation message in FTS5."""
    if not content.strip():
        return
    ts = ts or datetime.now(timezone.utc).isoformat()
    conn = None
    try:
        with _lock:
            conn = _ensure_db()
            conn.execute(
                "INSERT INTO messages_fts (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
                (session_id, role, content[:2000], ts),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("FTS index failed: {}", exc)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def index_session(session_id: str, messages: list[dict]) -> int:
    """Index all messages in a session. Returns count indexed."""
    count = 0
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        ts = m.get("ts", "")
        if content.strip():
            index_message(session_id, role, content, str(ts))
            count += 1
    return count


def search(query: str, limit: int = 20) -> list[dict]:
    """Search conversation history. Returns list of {session_id, role, content, ts, rank}."""
    if not query.strip():
        return []
    conn = None
    try:
        conn = _ensure_db()
        rows = conn.execute(
            "SELECT session_id, role, content, ts, rank "
            "FROM messages_fts WHERE messages_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [
            {"session_id": r[0], "role": r[1], "content": r[2], "ts": r[3], "rank": r[4]}
            for r in rows
        ]
    except sqlite3.OperationalError as exc:
        logger.debug("FTS query parse error: {}", exc)
        return []
    except Exception as exc:
        logger.warning("FTS search failed: {}", exc)
        return []
    finally:
        if conn:
            conn.close()
