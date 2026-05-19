# SPDX-License-Identifier: MIT
"""BugTracker abstract base — unified contract for all tracker adapters.

Currently implemented: Zentao (zentao_bug_manager.py).
Phase 2: Jira, GitHub Issues, Linear, Webhook — all implemented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BugTrackerBase(ABC):
    """Every tracker adapter MUST implement these 5 methods.

    Severity mapping (cross-tracker canonical):
      1 = P0 / Highest / Critical
      2 = P1 / High
      3 = P2 / Medium
      4 = P3 / Low
    """

    @abstractmethod
    def submit_bug(self, title: str, description: str, severity: int,
                   attachments: list[str] | None = None,
                   reproduce_steps: str = "") -> str:
        """Create a bug. Returns bug_id."""
        ...

    @abstractmethod
    def get_status(self, bug_id: str) -> dict[str, Any]:
        """Return {status, assignee, severity, last_updated}."""
        ...

    @abstractmethod
    def add_comment(self, bug_id: str, comment: str,
                    attachments: list[str] | None = None) -> None:
        ...

    @abstractmethod
    def link_testcase(self, bug_id: str, testcase_id: str) -> None:
        ...

    @abstractmethod
    def query_open_bugs(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        ...


TRACKER_REGISTRY: dict[str, type[BugTrackerBase]] = {}

try:
    from zentao_bug_manager import ZentaoBugManager  # noqa: F811
    TRACKER_REGISTRY["zentao"] = ZentaoBugManager
except ImportError:
    pass

try:
    from jira_bug_manager import JiraBugManager  # noqa: F811
    TRACKER_REGISTRY["jira"] = JiraBugManager
except ImportError:
    pass

try:
    from github_bug_manager import GitHubBugManager  # noqa: F811
    TRACKER_REGISTRY["github"] = GitHubBugManager
except ImportError:
    pass

try:
    from linear_bug_manager import LinearBugManager  # noqa: F811
    TRACKER_REGISTRY["linear"] = LinearBugManager
except ImportError:
    pass

try:
    from webhook_bug_manager import WebhookBugManager  # noqa: F811
    TRACKER_REGISTRY["webhook"] = WebhookBugManager
except ImportError:
    pass


def create_bug_manager(tracker: str = "", **kwargs: Any) -> BugTrackerBase | None:
    """Factory: return a BugTrackerBase adapter for the given tracker name.

    Falls back to BUG_TRACKER env var. Returns None if tracker unavailable.
    """
    import os

    name = tracker or os.getenv("BUG_TRACKER", "zentao")
    cls = TRACKER_REGISTRY.get(name)
    if cls is None:
        return None
    return cls(**kwargs)
