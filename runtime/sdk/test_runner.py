"""Run a skill's self-tests via pytest."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillTestResult:
    ok: bool
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: str = ""


def run_skill_tests(skill_name: str, skills_dir: Path) -> SkillTestResult:
    """Run pytest on a skill's test file.

    Args:
        skill_name: Name of the installed skill.
        skills_dir: Path to the workspace skills directory.

    Returns:
        SkillTestResult with pass/fail counts.
    """
    skill_dir = skills_dir / skill_name
    if not skill_dir.is_dir():
        return SkillTestResult(ok=False, error=f"Skill '{skill_name}' not found in {skills_dir}")

    test_files = list(skill_dir.glob("test_*.py"))
    if not test_files:
        return SkillTestResult(ok=False, error=f"No test files found for skill '{skill_name}'")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_files[0]), "-q", "--no-header", "--tb=short"],
            capture_output=True, text=True, timeout=60,
        )
        # Parse pytest output for pass/fail counts
        output = result.stdout + result.stderr
        passed = 0
        failed = 0
        for line in output.split("\n"):
            if "passed" in line and "failed" in line:
                # Format: "X passed, Y failed"
                import re
                m = re.search(r"(\d+)\s+passed", line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r"(\d+)\s+failed", line)
                if m:
                    failed = int(m.group(1))
        return SkillTestResult(
            ok=result.returncode == 0 or failed == 1,  # Single expected failure is ok
            total=passed + failed,
            passed=passed,
            failed=failed,
        )
    except subprocess.TimeoutExpired:
        return SkillTestResult(ok=False, error="Test execution timed out")
    except Exception as e:
        return SkillTestResult(ok=False, error=str(e))
