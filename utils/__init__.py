# SPDX-License-Identifier: MIT
"""Test-Agent utils package."""

import sys as _sys
from pathlib import Path as _Path

# Ensure project root is importable regardless of cwd.
# Replaces 9 scattered sys.path.insert calls across utils/ submodules.
_project_root = str(_Path(__file__).resolve().parent.parent)
if _project_root not in _sys.path:
    _sys.path.insert(0, _project_root)

import logging as _logging
import types as _types


class _LoguruBridge(_logging.Handler):
    """Redirect stdlib logging records to loguru."""

    def emit(self, record: _logging.LogRecord) -> None:
        try:
            from loguru import logger as _loguru_logger
        except ImportError:
            return
        try:
            level = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame: _types.FrameType | None = _logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == _logging.__file__:
            frame = frame.f_back
            depth += 1
        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


_root = _logging.getLogger()
if not any(isinstance(h, _LoguruBridge) for h in _root.handlers):
    _root.addHandler(_LoguruBridge())
