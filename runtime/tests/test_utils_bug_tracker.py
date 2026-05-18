# SPDX-License-Identifier: MIT
"""Unit tests for bug_tracker_base.py ABC and factory."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_utils_dir = Path(__file__).resolve().parents[2] / "05-代码示例"
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))


class TestBugTrackerBase:
    def test_cannot_instantiate_abstract(self):
        from bug_tracker_base import BugTrackerBase
        with pytest.raises(TypeError):
            BugTrackerBase()  # type: ignore[abstract]

    def test_concrete_subclass_instantiable(self):
        from bug_tracker_base import BugTrackerBase

        class FakeTracker(BugTrackerBase):
            def submit_bug(self, title, description, severity, attachments=None, reproduce_steps=""):
                return "BUG-1"

            def get_status(self, bug_id):
                return {"status": "open", "assignee": "", "severity": 3, "last_updated": ""}

            def add_comment(self, bug_id, comment, attachments=None):
                pass

            def link_testcase(self, bug_id, testcase_id):
                pass

            def query_open_bugs(self, filters=None):
                return []

        tracker = FakeTracker()
        assert tracker.submit_bug("test", "desc", 1) == "BUG-1"
        assert tracker.get_status("BUG-1")["status"] == "open"

    def test_missing_method_fails(self):
        from bug_tracker_base import BugTrackerBase

        class IncompleteTracker(BugTrackerBase):
            def submit_bug(self, title, description, severity, attachments=None, reproduce_steps=""):
                return ""

        with pytest.raises(TypeError):
            IncompleteTracker()  # type: ignore[abstract]


class TestTrackerRegistry:
    def test_zentao_registered(self):
        from bug_tracker_base import TRACKER_REGISTRY
        assert "zentao" in TRACKER_REGISTRY

    def test_jira_registered(self):
        from bug_tracker_base import TRACKER_REGISTRY
        assert "jira" in TRACKER_REGISTRY

    def test_github_registered(self):
        from bug_tracker_base import TRACKER_REGISTRY
        assert "github" in TRACKER_REGISTRY

    def test_linear_registered(self):
        from bug_tracker_base import TRACKER_REGISTRY
        assert "linear" in TRACKER_REGISTRY

    def test_webhook_registered(self):
        from bug_tracker_base import TRACKER_REGISTRY
        assert "webhook" in TRACKER_REGISTRY

    def test_all_registry_values_are_basetracker_subclasses(self):
        from bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY
        for name, cls in TRACKER_REGISTRY.items():
            if name == "zentao":
                # Legacy: ZentaoBugManager not yet migrated to BugTrackerBase ABC
                continue
            assert issubclass(cls, BugTrackerBase), f"{name}: {cls} not a BugTrackerBase subclass"


class TestCreateBugManager:
    def test_returns_none_for_unknown_tracker(self, monkeypatch):
        monkeypatch.delenv("BUG_TRACKER", raising=False)
        from bug_tracker_base import create_bug_manager
        assert create_bug_manager("nonexistent-tracker") is None

    def test_returns_instance_for_webhook(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_BUG_URL", "https://example.com/webhook")
        from bug_tracker_base import create_bug_manager
        mgr = create_bug_manager("webhook")
        assert mgr is not None
        assert type(mgr).__name__ == "WebhookBugManager"
