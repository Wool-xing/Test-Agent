"""Alembic env — only valid when run by `alembic` CLI, not for direct import."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from runtime.config.settings import get_settings
from runtime.storage.models import Base

target_metadata = Base.metadata

# Guard: all context.* calls fail on direct import (proxy not established).
# Only alembic CLI sets up the EnvironmentContext before loading this file.
try:
    config = context.config
except AttributeError:
    config = None  # type: ignore[assignment]

if config is not None:
    if config.config_file_name:
        fileConfig(config.config_file_name)
    config.set_main_option("sqlalchemy.url", get_settings().db_url)


def run_migrations_offline() -> None:
    if config is None:
        return
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if config is None:
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if config is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
