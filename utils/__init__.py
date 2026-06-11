# SPDX-License-Identifier: MIT
"""Test-Agent utils package."""

import logging as _logging


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
        frame: _logging.FrameType | None = _logging.currentframe()
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
