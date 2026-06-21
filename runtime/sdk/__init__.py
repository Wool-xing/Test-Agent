"""Skill SDK — create, validate, package, publish Skills for Test-Agent V2.0.0.

Sprint 3: 扩展体系

Public API:
    from runtime.sdk import scaffold_skill, validate_skill, package_skill, publish_skill
"""

from runtime.sdk.scaffold import scaffold_skill
from runtime.sdk.validate import validate_skill, ValidationResult
from runtime.sdk.package import package_skill
from runtime.sdk.publish import publish_skill, PublishResult
from runtime.sdk.discovery import discover_skills
from runtime.sdk.install import install_skill, InstallResult
from runtime.sdk.test_runner import run_skill_tests, SkillTestResult
from runtime.sdk.marketplace import (
    init_marketplace,
    publish_to_marketplace,
    search_marketplace,
    list_marketplace,
    MarketplaceEntry,
    MarketplaceResult,
)

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
