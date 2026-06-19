"""BugTrackerBase contract (mirrors utils/bug_manager.py 5 adapter).

实现该 5 方法才能注册。
severity 映射统一权威 (`utils/bug_severity_map.py`): 1=P0 / 2=P1 / 3=P2 / 4=P3.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BugRecord:
    bug_id: str
    title: str
    severity: int  # 1..4
    status: str
    assignee: str | None = None
    url: str | None = None
    last_updated: str | None = None
    extra: dict[str, Any] | None = None


class BugTrackerBase(abc.ABC):
    @abc.abstractmethod
    def submit_bug(
        self,
        title: str,
        description: str,
        severity: int,
        *,
        attachments: list[str] | None = None,
        reproduce_steps: str | None = None,
        **kwargs,
    ) -> str: ...

    @abc.abstractmethod
    def get_status(self, bug_id: str) -> BugRecord: ...

    @abc.abstractmethod
    def add_comment(self, bug_id: str, comment: str, *, attachments: list[str] | None = None) -> None: ...

    @abc.abstractmethod
    def link_testcase(self, bug_id: str, testcase_id: str | int) -> None: ...

    @abc.abstractmethod
    def query_open_bugs(self, *, filters: dict | None = None) -> list[BugRecord]: ...


ADAPTERS: dict[str, type[BugTrackerBase]] = {}


def register(name: str):
    def deco(cls: type[BugTrackerBase]):
        ADAPTERS[name] = cls
        return cls

    return deco


def get_adapter(name: str) -> BugTrackerBase:
    cls = ADAPTERS.get(name)
    if cls is None:
        raise KeyError(f"unknown bug tracker: {name}; available={list(ADAPTERS)}")
    return cls()
