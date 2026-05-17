"""
Compliance engine — read profiles/compliance/*.yaml and enforce checks programmatically.

Each YAML profile defines:
- standard: regulation name (GDPR, HIPAA, PCI-DSS, etc.)
- checks: list of {id, name, severity, check_type, rule}

Engine evaluates each check against the project and produces a compliance report.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CheckResult:
    check_id: str
    name: str
    standard: str
    severity: str  # P0 | P1 | P2
    passed: bool | None = None  # None = manual review required
    evidence: str = ""


@dataclass
class ComplianceReport:
    standard: str
    profile_path: str
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    manual: int = 0
    score: float = 0.0
    results: list[CheckResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": self.standard,
            "profile_path": self.profile_path,
            "total_checks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "manual": self.manual,
            "score": self.score,
            "results": [{
                "check_id": r.check_id,
                "name": r.name,
                "severity": r.severity,
                "passed": r.passed,
                "evidence": r.evidence,
            } for r in self.results],
        }


# ═══════════════════════════════════════════════════════════════
# Profile loader
# ═══════════════════════════════════════════════════════════════

def _profiles_dir() -> Path:
    """Resolve profiles/compliance/ relative to project root."""
    return Path(__file__).resolve().parents[2] / "profiles" / "compliance"


def load_profile(standard: str) -> dict[str, Any] | None:
    """Load a single compliance profile by standard name."""
    profile_paths = list(_profiles_dir().glob(f"{standard}*.yaml"))
    if not profile_paths:
        profile_paths = list(_profiles_dir().glob(f"{standard.lower()}*.yaml"))
    if not profile_paths:
        return None
    with open(profile_paths[0], encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_profiles() -> list[str]:
    """List all available compliance profiles."""
    return sorted([p.stem for p in _profiles_dir().glob("*.yaml")])


# ═══════════════════════════════════════════════════════════════
# Auto-checks (programmatic enforcement)
# ═══════════════════════════════════════════════════════════════

def _check_env_file() -> CheckResult:
    """Check that .env is git-ignored."""
    gitignore = Path(".gitignore")
    if not gitignore.exists():
        return CheckResult("env-gitignore", ".env in .gitignore", "Security Baseline",
                           "P0", False, ".gitignore not found")
    content = gitignore.read_text(encoding="utf-8")
    if ".env" in content:
        return CheckResult("env-gitignore", ".env in .gitignore", "Security Baseline",
                           "P0", True, ".env found in .gitignore")
    return CheckResult("env-gitignore", ".env in .gitignore", "Security Baseline",
                       "P0", False, ".env NOT in .gitignore")


def _check_no_hardcoded_secrets(scan_dir: str = ".") -> CheckResult:
    """Scan for hardcoded secrets patterns."""
    secret_patterns = [
        (r'(?:api[_-]?key|apikey|API_KEY)\s*[:=]\s*["\'][A-Za-z0-9_\-]{20,}', "API key"),
        (r'(?:password|passwd)\s*[:=]\s*["\'][^"\']+["\']', "password"),
        (r'(?:secret|SECRET)\s*[:=]\s*["\'][A-Za-z0-9_\-]{10,}', "secret"),
        (r'sk-[A-Za-z0-9]{32,}', "OpenAI key"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub token"),
    ]
    findings = []
    root = Path(scan_dir)
    for py_file in root.rglob("*.py"):
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            for pattern, label in secret_patterns:
                if re.search(pattern, content):
                    findings.append(f"{py_file}: {label}")
        except Exception:
            pass

    if findings:
        return CheckResult("no-hardcoded-secrets", "No hardcoded secrets",
                           "Security Baseline", "P0", False,
                           f"Found {len(findings)} potential secrets: {findings[:3]}")
    return CheckResult("no-hardcoded-secrets", "No hardcoded secrets",
                       "Security Baseline", "P0", True, "No secrets found")


def _check_license() -> CheckResult:
    """Check that LICENSE file exists."""
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
        if Path(name).exists():
            return CheckResult("license-file", "License file exists",
                               "OSS Compliance", "P1", True, name)
    return CheckResult("license-file", "License file exists",
                       "OSS Compliance", "P1", False, "No LICENSE file found")


def _check_readme() -> CheckResult:
    """Check that README exists."""
    for name in ["README.md", "README.zh-CN.md", "README.txt"]:
        if Path(name).exists():
            return CheckResult("readme-exists", "README exists",
                               "Documentation", "P1", True, name)
    return CheckResult("readme-exists", "README exists",
                       "Documentation", "P1", False, "No README found")


# ═══════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════

AUTO_CHECKS = [_check_env_file, _check_no_hardcoded_secrets, _check_license, _check_readme]


def run_compliance_check(standard: str | None = None,
                         project_dir: str = ".") -> ComplianceReport:
    """Run compliance checks against project.

    If standard is None, run all available profiles.
    """
    if standard:
        profile = load_profile(standard)
        if profile is None:
            report = ComplianceReport(standard=standard, profile_path="")
            report.results = [CheckResult("not-found", "Profile not found", standard, "P0", False)]
            report.total_checks = 1
            report.failed = 1
            return report
        return _evaluate_profile(profile)

    # Run all profiles
    merged = ComplianceReport(standard="all", profile_path="")
    for profile_name in list_profiles():
        profile = load_profile(profile_name)
        if profile:
            r = _evaluate_profile(profile)
            merged.total_checks += r.total_checks
            merged.passed += r.passed
            merged.failed += r.failed
            merged.manual += r.manual
            merged.results.extend(r.results)

    if merged.total_checks > 0:
        merged.score = round(merged.passed / merged.total_checks * 100, 1)
    return merged


def _evaluate_profile(profile: dict[str, Any]) -> ComplianceReport:
    """Evaluate a single compliance profile."""
    standard = profile.get("standard", "Unknown")
    checks_yml = profile.get("checks", [])

    report = ComplianceReport(
        standard=standard,
        profile_path=profile.get("_source", ""),
        total_checks=len(checks_yml) + len(AUTO_CHECKS),
    )

    # Run YAML-defined checks (currently all manual since they're skeleton)
    for chk in checks_yml:
        result = CheckResult(
            check_id=chk.get("id", ""),
            name=chk.get("name", ""),
            standard=standard,
            severity=chk.get("severity", "P0"),
            passed=None,  # Manual review needed
            evidence="manual review required — profile is skeleton",
        )
        report.results.append(result)
        report.manual += 1

    # Run auto-checks
    one_time = os.getcwd
    try:
        os.getcwd = lambda: str(Path.cwd())  # no-op, use actual cwd
    except Exception:
        pass
    for auto_fn in AUTO_CHECKS:
        result = auto_fn()
        report.results.append(result)
        if result.passed is True:
            report.passed += 1
        elif result.passed is False:
            report.failed += 1
        else:
            report.manual += 1

    if report.total_checks > 0:
        report.score = round(report.passed / report.total_checks * 100, 1)
    return report


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Compliance engine")
    ap.add_argument("--standard", default=None, help="Specific standard (or omit for all)")
    ap.add_argument("--output", default="", help="Output JSON file")
    ap.add_argument("--json", action="store_true", help="Print JSON to stdout")
    args = ap.parse_args()

    report = run_compliance_check(args.standard)
    result = report.to_dict()

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report written to {args.output}")

    if args.json or not args.output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Standard: {report.standard}")
        print(f"Score: {report.score}% ({report.passed}P/{report.failed}F/{report.manual}M)")
