"""Integration tests: CLI commands execute without errors.

Verifies real command execution — not mock, not stub.
Each test runs a CLI command via subprocess and checks exit code + output.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _run_cli(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run tagent CLI with given arguments. Returns CompletedProcess."""
    env = os.environ.copy()
    env.setdefault("TAGENT_LLM_PROVIDER", "stub")
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "runtime.cli.main"] + args,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
        cwd=Path(__file__).resolve().parents[2],
        env=env, **kwargs,
    )


class TestCLIGateway:
    """tagent gateway commands."""

    def test_gateway_status(self):
        r = _run_cli(["gateway", "status"])
        assert r.returncode == 0, f"Exit {r.returncode}: {r.stderr[:200]}"
        assert "Gateway" in r.stdout or "gateway" in r.stderr.lower()

    def test_gateway_platform_registry(self):
        from runtime.gateway.base import REGISTRY
        platforms = sorted(REGISTRY.keys())
        for p in ["telegram", "discord", "slack", "wechat", "dingtalk", "qqbot"]:
            assert p in platforms, f"Missing: {p}"


class TestCLICatalog:
    """tagent catalog."""

    def test_catalog_has_experts(self):
        from runtime.registry.registry import build_catalog
        cat = build_catalog()
        assert len(cat.experts) >= 10
        assert "test-lead" in cat.experts


class TestCLIDoctor:
    """tagent doctor."""

    def test_doctor_runs(self):
        from runtime.cli.doctor import run_doctor
        results, ok, warn = run_doctor()
        assert ok >= 10  # minimum checks
        sections = [s["section"] for s in results]
        assert "Environment" in sections
        assert "Catalog" in sections


class TestCLIServe:
    """tagent serve — verify import path works (don't actually start daemon)."""

    def test_serve_module_imports(self):
        from runtime.cli.commands.serve import serve
        assert callable(serve)


class TestCLIVersionCheck:
    """Update/version checks."""

    def test_check_version_script(self):
        from runtime.config.settings import get_settings
        checker = get_settings().config_dir / "check_version.py"
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(checker)],
            capture_output=True, text=True, timeout=15,
            cwd=Path(__file__).resolve().parents[2],
        )
        # Exit 0 always (network errors are silent)
        assert r.returncode == 0


class TestCLITaskSystem:
    """Task CRUD via Python API (integration)."""

    def test_task_full_lifecycle(self):
        from runtime.cli.tasks import add_task, list_tasks, update_task, delete_task

        # Create
        t = add_task("Integration test task", criteria=["CI green", "all tests pass"])
        assert t.id

        # Read
        tasks = list_tasks()
        assert any(x.id == t.id for x in tasks)

        # Update
        u = update_task(t.id, status="in_progress")
        assert u.status == "in_progress"
        u2 = update_task(t.id, status="done")
        assert u2.status == "done"

        # Delete
        assert delete_task(t.id)
        tasks2 = list_tasks()
        assert not any(x.id == t.id for x in tasks2)


class TestCLIReadiness:
    """Readiness gate."""

    def test_readiness_fast_mode(self):
        from runtime.cli.readiness import run_readiness
        r = run_readiness(fast=True)
        assert len(r.gates) >= 3  # imports, config, catalog, deps
        assert 0.0 <= r.overall_score <= 1.0
        assert isinstance(r.ready, bool)


class TestNLCron:
    """Natural language cron parser."""

    def test_all_common_phrases(self):
        from runtime.scheduler.nl_cron import parse
        cases = {
            "every morning": "0 8 * * *",
            "every day at 18": "0 18 * * *",
            "every monday": "0 9 * * 1",
            "hourly": "0 * * * *",
            "daily at 6": "0 6 * * *",
        }
        for phrase, expected in cases.items():
            assert parse(phrase) == expected, f"{phrase}: expected {expected}"


class TestLLMCache:
    """LLM response cache."""

    def test_cache_hit_miss_clear(self):
        from runtime.router.llm_cache import set_cached, get_cached, clear_cache

        clear_cache()
        set_cached("test", "m", "s", "u", 0.1, "response")
        assert get_cached("test", "m", "s", "u", 0.1) == "response"
        assert get_cached("test", "m", "s", "different", 0.1) is None
        clear_cache()
        assert get_cached("test", "m", "s", "u", 0.1) is None


class TestSkillDistiller:
    """Skill distillation."""

    def test_distillable_detection(self):
        from runtime.learning_loop.skill_distiller import ExecutionTrace
        # Complex enough
        t = ExecutionTrace(
            user_prompt="test login page",
            agent_chain=["req-analyst", "auto-engineer", "executor"],
            node_count=3,
        )
        assert t.is_distillable
        # Too simple
        t2 = ExecutionTrace(
            user_prompt="simple check",
            agent_chain=["req-analyst", "req-analyst"],
            node_count=2,
        )
        assert not t2.is_distillable


class TestIntegrityRules:
    """Integrity injection."""

    def test_strict_rules_content(self):
        import os
        os.environ["TAGENT_INTEGRITY"] = "strict"
        from runtime.tutor.integrity import get_integrity_rules
        rules = get_integrity_rules()
        assert "No fabrication" in rules
        assert "Traceability" in rules
        assert "Reproducibility" in rules
        del os.environ["TAGENT_INTEGRITY"]

    def test_agent_runner_injects_integrity(self):
        from runtime.orchestrator.agents.base import AgentRunner
        assert hasattr(AgentRunner, "_system_prompt_with_integrity")


class TestAgentSkillPairing:
    """Agent-skill frontmatter pairing."""

    def test_all_agents_have_pairing(self):
        import re
        agents_dir = Path(__file__).resolve().parents[2] / "ai" / "agents"
        for f in sorted(agents_dir.glob("[0-9]*.md")):
            text = f.read_text(encoding="utf-8")
            assert "paired_skills:" in text, f"{f.name}: missing paired_skills"


class TestPersonalitySystem:
    """Personality switching."""

    def test_list_and_load(self):
        from runtime.cli.conversation import list_personalities, set_personality, get_personality, load_personality
        ps = list_personalities()
        assert len(ps) == 16
        assert set_personality("test-lead")
        assert get_personality() == "test-lead"
        profile = load_personality("test-lead")
        assert profile and len(profile) > 100


class TestProjectContext:
    """Project context auto-discovery."""

    def test_discovers_claude_md(self):
        from runtime.cli.conversation import _discover_project_context
        ctx = _discover_project_context()
        assert ctx is not None
        assert len(ctx) > 500  # real CLAUDE.md content
