"""TDD tests for utils/trackers/ — BugTrackerBase, TRACKER_REGISTRY, create_bug_manager.

Tests the tracker abstraction layer without requiring actual API credentials.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
# BugTrackerBase contract
# ═══════════════════════════════════════════════════════════════════════════

class TestBugTrackerBase:
    def test_base_is_abstract(self):
        """BugTrackerBase should be an ABC and cannot be instantiated."""
        from utils.trackers.bug_tracker_base import BugTrackerBase
        with pytest.raises(TypeError):
            BugTrackerBase()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_all(self):
        """Subclasses missing abstract methods should fail instantiation."""
        from utils.trackers.bug_tracker_base import BugTrackerBase

        class IncompleteTracker(BugTrackerBase):
            def submit_bug(self, title, description, severity, **kw):
                return "bug-1"

        with pytest.raises(TypeError):
            IncompleteTracker()

    def test_full_subclass_instantiates(self):
        """Subclass implementing all 5 methods should instantiate."""
        from utils.trackers.bug_tracker_base import BugTrackerBase

        class FullTracker(BugTrackerBase):
            def submit_bug(self, title, description, severity, **kw):
                return "bug-001"

            def get_status(self, bug_id):
                return {"status": "open"}

            def add_comment(self, bug_id, comment, **kw):
                pass

            def link_testcase(self, bug_id, testcase_id):
                pass

            def query_open_bugs(self, filters=None):
                return []

        tracker = FullTracker()
        bug_id = tracker.submit_bug("crash", "details", 1)
        assert bug_id == "bug-001"

    def test_subclass_can_accept_kwargs(self):
        """Subclass __init__ should accept tracker-specific kwargs."""
        from utils.trackers.bug_tracker_base import BugTrackerBase

        class ConfigurableTracker(BugTrackerBase):
            def __init__(self, url="", token="", **kw):
                self.url = url
                self.token = token

            def submit_bug(self, title, description, severity, **kw):
                return f"{self.url}/bugs/1"

            def get_status(self, bug_id):
                return {"status": "open"}

            def add_comment(self, bug_id, comment, **kw):
                pass

            def link_testcase(self, bug_id, testcase_id):
                pass

            def query_open_bugs(self, filters=None):
                return []

        tracker = ConfigurableTracker(url="https://jira.example.com", token="secret")
        assert tracker.url == "https://jira.example.com"


# ═══════════════════════════════════════════════════════════════════════════
# TRACKER_REGISTRY + create_bug_manager
# ═══════════════════════════════════════════════════════════════════════════

class TestTrackerRegistry:
    def test_registry_is_dict(self):
        """TRACKER_REGISTRY should be a dict."""
        from utils.trackers.bug_tracker_base import TRACKER_REGISTRY
        assert isinstance(TRACKER_REGISTRY, dict)

    def test_registry_has_zentao(self):
        """TRACKER_REGISTRY should contain zentao entry."""
        from utils.trackers.bug_tracker_base import TRACKER_REGISTRY
        assert "zentao" in TRACKER_REGISTRY, f"Registry keys: {list(TRACKER_REGISTRY.keys())}"

    def test_create_bug_manager_unknown_tracker(self):
        """create_bug_manager for unknown tracker returns None."""
        import os as _os

        from utils.trackers.bug_tracker_base import create_bug_manager
        old = _os.environ.get("BUG_TRACKER", "")
        _os.environ["BUG_TRACKER"] = "nonexistent_tracker_xyz"
        try:
            result = create_bug_manager()
            assert result is None
        finally:
            _os.environ["BUG_TRACKER"] = old

    def test_create_bug_manager_unknown_explicit(self):
        """create_bug_manager with explicit unknown name returns None."""
        # Pass a tracker name that definitely doesn't exist
        import os as _os

        from utils.trackers.bug_tracker_base import create_bug_manager
        old = _os.environ.get("BUG_TRACKER", "")
        _os.environ["BUG_TRACKER"] = ""
        try:
            result = create_bug_manager("unknown-tracker-xyz")
            assert result is None
        finally:
            _os.environ["BUG_TRACKER"] = old

    def test_zentao_in_registry_is_class(self):
        """Zentao entry in registry should be a class."""
        from utils.trackers.bug_tracker_base import TRACKER_REGISTRY
        cls = TRACKER_REGISTRY.get("zentao")
        assert cls is not None
        assert isinstance(cls, type)


# ═══════════════════════════════════════════════════════════════════════════
# ZentaoBugManager basic contract
# ═══════════════════════════════════════════════════════════════════════════

class TestZentaoBugManager:
    def test_imports(self):
        """ZentaoBugManager should be importable."""
        try:
            from utils.trackers.zentao_bug_manager import ZentaoBugManager
            assert ZentaoBugManager is not None
        except ImportError:
            pytest.skip("ZentaoBugManager not importable")

    def test_has_core_methods(self):
        """ZentaoBugManager should expose bug creation and query methods."""
        try:
            from utils.trackers.zentao_bug_manager import ZentaoBugManager
        except ImportError:
            pytest.skip("ZentaoBugManager not importable")

        # ZenTao uses create_bug instead of submit_bug — adapter pattern
        assert hasattr(ZentaoBugManager, "create_bug") or hasattr(ZentaoBugManager, "submit_bug")
        assert hasattr(ZentaoBugManager, "get_bug") or hasattr(ZentaoBugManager, "get_status")


# ═══════════════════════════════════════════════════════════════════════════
# JiraBugManager basic contract
# ═══════════════════════════════════════════════════════════════════════════

class TestJiraBugManager:
    def test_registry_entry_may_be_absent(self):
        """Jira may not be in registry if jira package not installed — that's OK."""
        from utils.trackers.bug_tracker_base import TRACKER_REGISTRY
        if "jira" not in TRACKER_REGISTRY:
            pytest.skip("JiraBugManager not registered (jira package not installed)")

    def test_has_required_methods(self):
        """JiraBugManager should implement all BugTrackerBase methods."""
        from utils.trackers.bug_tracker_base import TRACKER_REGISTRY
        cls = TRACKER_REGISTRY.get("jira")
        if cls is None:
            pytest.skip("JiraBugManager not registered")
        for method in ["submit_bug", "get_status", "add_comment", "link_testcase", "query_open_bugs"]:
            assert hasattr(cls, method), f"Missing method: {method}"


# ═══════════════════════════════════════════════════════════════════════════
# Severity mapping contract
# ═══════════════════════════════════════════════════════════════════════════

class TestSeverityMapping:
    def test_severity_contract(self):
        """Verify the cross-tracker severity mapping is documented in base class."""
        from utils.trackers.bug_tracker_base import BugTrackerBase
        doc = BugTrackerBase.__doc__ or ""
        assert "P0" in doc or "1 =" in doc
        assert "P1" in doc or "2 =" in doc
        assert "P2" in doc or "3 =" in doc
        assert "P3" in doc or "4 =" in doc
