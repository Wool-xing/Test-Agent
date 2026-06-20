"""TDD tests for Deprecation Policy (§补-24)."""

import pytest

from runtime.infra.deprecation import (
    DeprecationRegistry,
    DeprecationEntry,
    DeprecationLevel,
    get_deprecation_registry,
)


class TestDeprecationRegistry:
    def test_register_and_check(self):
        """Should register and find deprecation entries."""
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry(
            name="old-command", level=DeprecationLevel.SOFT,
            message="Use new-command", removed_in_version="V2.3.0",
            replacement="tagent new-command", deprecated_since="V2.0.0",
        ))
        entry = reg.check("old-command")
        assert entry is not None
        assert entry.level == DeprecationLevel.SOFT
        assert entry.replacement == "tagent new-command"

    def test_check_nonexistent(self):
        """Should return None for non-deprecated features."""
        reg = DeprecationRegistry()
        assert reg.check("new-feature") is None

    def test_list_active(self):
        """Should list active (non-removed) deprecations."""
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("old", DeprecationLevel.SOFT, "", "V3.0"))
        reg.register(DeprecationEntry("gone", DeprecationLevel.REMOVED, "", "V2.0"))
        active = reg.list_active()
        assert len(active) == 1
        assert active[0].name == "old"

    def test_hard_blocked_without_flag(self):
        """Hard-deprecated should be blocked without opt-in flag."""
        reg = DeprecationRegistry()
        reg.register(DeprecationEntry("old-api", DeprecationLevel.HARD, "", "V3.0"))
        import os
        os.environ.pop("TAGENT_DEPRECATED_ALLOW_OLD_API", None)
        assert reg.is_hard_blocked("old-api") is True

    def test_singleton(self):
        """get_deprecation_registry should return singleton."""
        r1 = get_deprecation_registry()
        r2 = get_deprecation_registry()
        assert r1 is r2
