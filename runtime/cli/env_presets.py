"""Environment presets — save/load named environment configurations.

Persist to workspace/gateway/env_presets.json.
/env save <name>: snapshot current env vars into preset
/env load <name>: apply preset to current session
/env list: show all presets
/env delete <name>: remove a preset
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# Env vars that are captured in presets
CAPTURE_PREFIXES = [
    "TEST_", "STAGING_", "TAGENT_", "APP_", "DB_", "API_",
    "ZENTAO_", "JIRA_", "GITHUB_", "WECHAT_", "FEISHU_", "DINGTALK_",
    "PERF_", "COVERAGE_", "HEADLESS", "PARALLEL_", "LOG_LEVEL",
]


@dataclass
class EnvPreset:
    name: str
    description: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)
    created_at: float = 0.0


def _file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "env_presets.json"


def _load() -> list[dict]:
    p = _file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(presets: list[dict]) -> None:
    _file().write_text(json.dumps(presets, ensure_ascii=False, indent=2), encoding="utf-8")


def _capture_env() -> dict[str, str]:
    """Capture current env vars matching TEST_/STAGING_/TAGENT_ prefixes."""
    result: dict[str, str] = {}
    for key, val in os.environ.items():
        for prefix in CAPTURE_PREFIXES:
            if key.startswith(prefix):
                result[key] = val
                break
    return result


def list_presets() -> list[EnvPreset]:
    return [EnvPreset(**p) for p in _load()]


def save_preset(name: str, description: str = "") -> EnvPreset:
    import time
    preset = EnvPreset(
        name=name, description=description,
        env_vars=_capture_env(), created_at=time.time(),
    )
    presets = _load()
    # Replace if exists
    for i, p in enumerate(presets):
        if p.get("name") == name:
            presets[i] = asdict(preset)
            _save(presets)
            return preset
    presets.append(asdict(preset))
    _save(presets)
    return preset


def load_preset(name: str) -> EnvPreset | None:
    """Apply preset env vars to current process. Returns preset or None."""
    for p in _load():
        if p.get("name") == name:
            for k, v in p.get("env_vars", {}).items():
                os.environ[k] = v
            logger.info("env preset loaded: {} ({} vars)", name, len(p.get("env_vars", {})))
            return EnvPreset(**p)
    return None


def delete_preset(name: str) -> bool:
    presets = _load()
    for i, p in enumerate(presets):
        if p.get("name") == name:
            presets.pop(i)
            _save(presets)
            return True
    return False
