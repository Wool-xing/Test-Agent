"""Skill SDK — create, validate, package, publish Skills for Test-Agent V2.0.0.

Sprint 3: 扩展体系

Public API:
    from runtime.sdk import scaffold_skill, validate_skill, package_skill, publish_skill
"""

from runtime.sdk.discovery import discover_skills
from runtime.sdk.install import InstallResult, install_skill
from runtime.sdk.marketplace import (
    MarketplaceEntry,
    MarketplaceResult,
    init_marketplace,
    list_marketplace,
    publish_to_marketplace,
    search_marketplace,
)
from runtime.sdk.package import package_skill
from runtime.sdk.publish import PublishResult, publish_skill
from runtime.sdk.scaffold import scaffold_skill
from runtime.sdk.test_runner import SkillTestResult, run_skill_tests
from runtime.sdk.validate import ValidationResult, validate_skill

__all__ = [
    "scaffold_skill",
    "validate_skill",
    "ValidationResult",
    "package_skill",
    "publish_skill",
    "PublishResult",
    "discover_skills",
    "install_skill",
    "InstallResult",
    "run_skill_tests",
    "SkillTestResult",
    "init_marketplace",
    "publish_to_marketplace",
    "search_marketplace",
    "list_marketplace",
    "MarketplaceEntry",
    "MarketplaceResult",
]
