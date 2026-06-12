"""Verbosity mode

exec  = 默认,每节点仅 one_liner(≤30 字);可 --silent 关
learn = 全套教学:why + theory_ref + alternatives + reading + L3 反馈
"""

from __future__ import annotations

import os
from enum import Enum


class Mode(str, Enum):
    EXEC = "exec"
    LEARN = "learn"
    SILENT = "silent"


def get_mode() -> Mode:
    raw = os.getenv("TAGENT_MODE", "exec").lower()
    if raw in ("exec", "execute", "default", "run"):
        return Mode.EXEC
    if raw in ("learn", "tutorial", "study", "教学", "学习"):
        return Mode.LEARN
    if raw in ("silent", "quiet"):
        return Mode.SILENT
    return Mode.EXEC


def set_mode(mode: Mode | str) -> None:
    if isinstance(mode, str):
        mode = Mode(mode)
    os.environ["TAGENT_MODE"] = mode.value


def is_learn() -> bool:
    return get_mode() is Mode.LEARN


def is_silent() -> bool:
    return get_mode() is Mode.SILENT
