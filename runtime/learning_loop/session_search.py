"""FTS5 session search · .

SQLite FTS5 over historical sessions. LLM summary attached at retrieval time.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from runtime.config.settings import get_settings


def _db_path() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning"
    d.mkdir(parents=True, exist_ok=True)
    return d / "sessions.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_db_path())
    c.row_factory = sqlite3.Row
    return c


def _init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
                session_id UNINDEXED,
                run_id UNINDEXED,
                target_kind UNINDEXED,
                content,
                created_at UNINDEXED,
                tokenize='unicode61'
            );
            CREATE TABLE IF NOT EXISTS session_meta (
                session_id TEXT PRIMARY KEY,
                run_id TEXT,
                target_kind TEXT,
                summary TEXT,
                created_at TEXT,
                user TEXT
            );
            """
        )


def index_session(session_id: str, run_id: str, target_kind: str, content: str, *, user: str | None = None) -> None:
    _init_db()
    ts = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        c.execute(
            "INSERT INTO sessions_fts(session_id, run_id, target_kind, content, created_at) VALUES (?,?,?,?,?)",
            (session_id, run_id, target_kind, content, ts),
        )
        c.execute(
            "INSERT OR REPLACE INTO session_meta(session_id, run_id, target_kind, created_at, user) VALUES (?,?,?,?,?)",
            (session_id, run_id, target_kind, ts, user),
        )


def search(query: str, *, top_k: int = 5, target_kind: str | None = None) -> list[dict]:
    """FTS5 full-text search; return top_k hits with snippet + meta."""
    _init_db()
    sql = "SELECT session_id, run_id, target_kind, snippet(sessions_fts, 3, '[', ']', '...', 32) AS snippet, created_at FROM sessions_fts WHERE sessions_fts MATCH ?"
    args: list = [query]
    if target_kind:
        sql += " AND target_kind = ?"
        args.append(target_kind)
    sql += " ORDER BY rank LIMIT ?"
    args.append(top_k)
    with _conn() as c:
        rows = c.execute(sql, args).fetchall()
        return [dict(r) for r in rows]


def attach_summary(session_id: str, summary: str) -> None:
    _init_db()
    with _conn() as c:
        c.execute("UPDATE session_meta SET summary = ? WHERE session_id = ?", (summary, session_id))


def get_meta(session_id: str) -> dict | None:
    _init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM session_meta WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row) if row else None
