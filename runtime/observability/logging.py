"""Loguru config: structured (json) when TAGENT_LOG_JSON=1, else human-readable."""

from __future__ import annotations

import os
import sys

from loguru import logger

_configured = False


def configure_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    logger.remove()
    if os.getenv("TAGENT_LOG_JSON", "0") == "1":
        logger.add(sys.stdout, serialize=True, level=level)
    else:
        logger.add(
            sys.stdout,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level:<7}</level> | "
                "<cyan>{name}:{function}:{line}</cyan> | "
                "{message}"
            ),
        )
    _configured = True


def bind_run(run_id: str):
    """Returns a logger bound to a run_id for tracing one execution."""
    return logger.bind(run_id=run_id)
