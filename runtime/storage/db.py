"""SQLAlchemy engine + session factory."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from runtime.config.settings import get_settings

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().db_url
        kw: dict = {"pool_pre_ping": True}
        # Short connect timeout for psycopg to avoid hanging on unavailable DB
        if url.startswith("postgresql"):
            kw["connect_args"] = {"connect_timeout": 5}
        _engine = create_engine(url, **kw)
        _init_schema(_engine, url)
    return _engine


def _init_schema(engine, url: str) -> None:
    """Ensure schema exists on first engine use (once per process).

    sqlite → create_all (test/offline fallback, no alembic needed).
    postgres → alembic upgrade head (migration adds pgvector extension + vector column).
    """
    if url.startswith("sqlite"):
        from runtime.storage.models import Base

        Base.metadata.create_all(engine)
    else:
        from pathlib import Path

        from alembic import command
        from alembic.config import Config
        from sqlalchemy import text
        from sqlalchemy.pool import NullPool

        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
        # Escape % — configparser BasicInterpolation would otherwise break
        # percent-encoded passwords (e.g. p%40ss) inside command.upgrade.
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

        # Serialize concurrent migrations across processes (multi-worker boot):
        # pg_advisory_lock on a dedicated non-pooled connection, so the lock is
        # released on close instead of leaking into the pool.
        lock_engine = create_engine(url, poolclass=NullPool)
        with lock_engine.connect() as lock_conn:
            lock_conn.execute(text("SELECT pg_advisory_lock(789456123)"))
            try:
                command.upgrade(cfg, "head")
            finally:
                lock_conn.execute(text("SELECT pg_advisory_unlock(789456123)"))
            lock_conn.commit()


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    s = get_sessionmaker()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
