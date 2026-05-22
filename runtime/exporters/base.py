"""Exporter base · TestCaseTree + Exporter ABC + registry.

TestCaseTree 是 LLM/testcase-designer 输出的统一中间表示;
每个 exporter 把它落到一种格式.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Priority = Literal["P0", "P1", "P2", "P3"]


@dataclass(slots=True)
class TestCaseNode:
    """Tree node · 可以是模块/特性/用例/步骤(由 kind 区分)."""

    title: str
    kind: Literal["module", "feature", "case", "step"] = "feature"
    priority: Priority | None = None
    preconditions: list[str] = field(default_factory=list)
    expected: list[str] = field(default_factory=list)
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    children: list[TestCaseNode] = field(default_factory=list)
    id: str = ""  # optional,LLM 可不填,exporter 自动生成


@dataclass(slots=True)
class TestCaseTree:
    """Top-level container."""

    project_name: str
    root: TestCaseNode
    version: str = "1.0"
    author: str = "Test-Agent"


class Exporter(abc.ABC):
    name: str = "abstract"
    extension: str = ".out"

    @abc.abstractmethod
    def export(self, tree: TestCaseTree, target: Path) -> Path:
        """Write tree to target; return final path."""


REGISTRY: dict[str, type[Exporter]] = {}


def register(name: str):
    def deco(cls: type[Exporter]):
        cls.name = name
        REGISTRY[name] = cls
        return cls

    return deco


def get_exporter(name: str) -> Exporter:
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"unknown exporter: {name}; available={sorted(REGISTRY)}")
    return cls()
