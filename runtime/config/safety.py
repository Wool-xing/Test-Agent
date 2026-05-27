"""Safe-by-default destructive guard · gbrain §1.9 派生.

危险/自动化/生产影响 操作必须 tagent.yml 显式开启.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml
from loguru import logger

from runtime.config.settings import get_settings


class SafeByDefaultBlocked(Exception):
    """Raised when an operation is gated and the user did not enable it in tagent.yml."""

    def __init__(self, op: str, key_path: str):
        super().__init__(f"operation '{op}' blocked: tagent.yml `{key_path}` not enabled (safe-by-default)")
        self.op = op
        self.key_path = key_path


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    s = get_settings()
    candidates = [
        s.project_root / "tagent.yml",
        s.project_root / "tagent.yaml",
        s.resolve(s.workspace_dir) / "tagent.yml",
    ]
    for p in candidates:
        if p.is_file():
            try:
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as e:
                logger.error("tagent.yml parse failed: {}", e)
                return {}
    return {}


def reload_config() -> None:
    """Drop the cache; next `get_safety()` rereads tagent.yml."""
    _load_config.cache_clear()


def _resolve(path: list[str], default: Any = None) -> Any:
    cfg = _load_config()
    cur: Any = cfg
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def assert_allowed(op: str, key_path: str, *, default: bool = False) -> None:
    """Raise SafeByDefaultBlocked unless tagent.yml has the key set to truthy."""
    keys = key_path.split(".")
    val = _resolve(keys, default=default)
    if not val:
        raise SafeByDefaultBlocked(op=op, key_path=key_path)


def is_allowed(key_path: str, *, default: bool = False) -> bool:
    keys = key_path.split(".")
    val = _resolve(keys, default=default)
    return bool(val)


def get_setting(key_path: str, default: Any = None) -> Any:
    return _resolve(key_path.split("."), default=default)


# Common gates (charter §24)
def gate_scheduler_tick() -> None:
    assert_allowed("scheduler.tick", "scheduler.enabled")


def gate_cron_auto_approve() -> None:
    assert_allowed("scheduler.cron_jobs_allowed", "scheduler.cron_jobs_allowed")


def gate_curator_run() -> None:
    assert_allowed("curator.run", "curator.enabled")


def gate_backend(name: str) -> None:
    allowed = get_setting("backends.allowed", default=["local"])
    if name not in allowed:
        raise SafeByDefaultBlocked(op=f"backend:{name}", key_path=f"backends.allowed +=[{name}]")


def gate_gateway_platform(name: str) -> None:
    enabled = get_setting("gateway.enabled_platforms", default=[])
    if name not in enabled:
        raise SafeByDefaultBlocked(op=f"gateway:{name}", key_path=f"gateway.enabled_platforms +=[{name}]")


def gate_destructive(op: str, *, key: str | None = None) -> None:
    key = key or f"destructive_ops.allow_{op}"
    assert_allowed(op, key)
