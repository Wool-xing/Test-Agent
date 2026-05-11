"""Load matrix.yaml · 单源真理读出来的结构化数据."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class TestTypeSpec:
    key: str
    label: str
    description: str
    default_skills: list[str]
    default_platform: str
    required_env: list[str]


@dataclass(slots=True)
class PlatformSpec:
    key: str
    label: str
    extras: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProviderSpec:
    key: str
    label: str
    env: dict[str, str]
    model_hint: str = ""


@dataclass(slots=True)
class TrackerSpec:
    key: str
    label: str
    env: dict[str, str]


@dataclass(slots=True)
class NotifierSpec:
    key: str
    label: str
    env: dict[str, str]


@dataclass(slots=True)
class Matrix:
    test_types: dict[str, TestTypeSpec]
    platforms: dict[str, PlatformSpec]
    llm_providers: dict[str, ProviderSpec]
    bug_trackers: dict[str, TrackerSpec]
    notifiers: dict[str, NotifierSpec]


def _matrix_path() -> Path:
    from runtime.config.settings import get_settings

    return get_settings().project_root / "04-配置文件" / "templates" / "matrix.yaml"


def load_matrix(path: Path | None = None) -> Matrix:
    p = path or _matrix_path()
    raw: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Matrix(
        test_types={
            k: TestTypeSpec(
                key=k,
                label=v["label"],
                description=v.get("description", ""),
                default_skills=list(v.get("default_skills", [])),
                default_platform=v.get("default_platform", "linux"),
                required_env=list(v.get("required_env", [])),
            )
            for k, v in (raw.get("test_types") or {}).items()
        },
        platforms={
            k: PlatformSpec(key=k, label=v["label"], extras=list(v.get("extras", [])))
            for k, v in (raw.get("platforms") or {}).items()
        },
        llm_providers={
            k: ProviderSpec(
                key=k,
                label=v["label"],
                env=dict(v.get("env", {})),
                model_hint=v.get("model_hint", ""),
            )
            for k, v in (raw.get("llm_providers") or {}).items()
        },
        bug_trackers={
            k: TrackerSpec(key=k, label=v["label"], env=dict(v.get("env", {})))
            for k, v in (raw.get("bug_trackers") or {}).items()
        },
        notifiers={
            k: NotifierSpec(key=k, label=v["label"], env=dict(v.get("env", {})))
            for k, v in (raw.get("notifiers") or {}).items()
        },
    )
