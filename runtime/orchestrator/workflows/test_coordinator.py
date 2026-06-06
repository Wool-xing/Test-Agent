"""Test Coordinator pipeline — 11-step automated workflow.

Implements skills/test-coordinator.md as executable code.
Reuses execute_node() from runtime.orchestrator.adapters.experts.
Gate enforcement between phases via runtime.orchestrator.workflows.gates.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.cli._shared import console
from runtime.orchestrator.workflows.gates import (
    GateResult,
    check_perf_gate,
    check_regression_gate,
    check_smoke_gate,
)

# Paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_WORKSPACE = _PROJECT_ROOT / "workspace"


@dataclass
class PipelineStep:
    name: str
    kind: str  # "expert" | "skill"
    status: str = "pending"  # pending | running | ok | failed | skipped
    output: str = ""
    duration_ms: float = 0


@dataclass
class PipelineResult:
    ok: bool
    steps: list[PipelineStep] = field(default_factory=list)
    aborted_at: str | None = None
    summary: str = ""


class TestCoordinatorPipeline:
    """Execute the 11-step test-coordinator pipeline.

    Usage:
        pipeline = TestCoordinatorPipeline()
        result = pipeline.run("path/to/prd.md")
    """

    # Step sequence from skills/test-coordinator.md
    SEQUENCE: list[tuple[str, str]] = [
        ("requirements-analyst", "expert"),
        ("testcase-designer", "skill"),
        ("env-manager", "expert"),
        ("data-preparer", "expert"),
        ("automation-engineer", "expert"),
        ("jmeter-script-gen", "skill"),
        ("smoke-test", "skill"),
        ("test-executor", "expert"),
        ("bug-manager", "expert"),
        ("report-generator", "expert"),
        ("test-lead", "expert"),
    ]

    def run(self, target: str) -> PipelineResult:
        """Execute the full pipeline per skills/test-coordinator.md."""
        result = PipelineResult(ok=True)
        run_id = f"tc-{int(time.time())}"
        console.print(f"[bold]Test Coordinator Pipeline[/] ({run_id})")
        console.print(f"Target: {target[:100]}{'...' if len(target) > 100 else ''}")
        console.print()

        # Validate target path (prevent traversal)
        if target and not target.startswith(("http://", "https://")):
            resolved = Path(target).resolve()
            if not str(resolved).startswith(str(_PROJECT_ROOT.resolve())):
                result.ok = False
                result.aborted_at = "preflight"
                result.summary = f"Target outside workspace: {target}"
                return result

        # Step 0: Pre-flight checklist (test-coordinator.md Step 0)
        platform_hints = self._detect_platform(target)
        missing = self._preflight(platform_hints)
        if missing:
            self._print_checklist(platform_hints, missing)
            result.ok = False
            result.aborted_at = "preflight"
            result.summary = f"Missing: {', '.join(missing)}"
            return result

        # Step 1: PRD load + platform identification (test-coordinator.md Step 1)
        prd_text = self._load_prd(target)
        routing = self._route_target(prd_text or target)
        console.print(f"[dim]Router → {routing}[/dim]")

        # Execute each step
        for i, (name, kind) in enumerate(self.SEQUENCE, 1):
            step = PipelineStep(name=name, kind=kind)
            result.steps.append(step)

            console.print(f"  [{i}/{len(self.SEQUENCE)}] {name}...", end=" ")
            try:
                # Step 4 (env-manager): retry on failure per test-coordinator.md
                if name == "env-manager":
                    outcome = self._execute_with_retry(name, kind, target)
                else:
                    outcome = self._execute_node(name, kind, target)
                step.status = "ok" if outcome.get("ok", True) else "failed"
                step.output = str(outcome.get("stdout", ""))[:200]
                step.duration_ms = outcome.get("duration_ms", 0)
                console.print(
                    f"[green]OK[/] ({step.duration_ms:.0f}ms)"
                    if step.status == "ok"
                    else "[red]FAILED[/]"
                )

                # Gate checks between phases
                gate_block = self._check_gates(name, outcome)
                if gate_block:
                    console.print(f"  [red]Gate BLOCK at {name}: {gate_block}[/]")
                    result.aborted_at = name
                    break
            except Exception as exc:
                step.status = "failed"
                step.output = str(exc)[:200]
                console.print(f"[red]ERROR: {exc}[/]")
                if i <= 3:
                    # Early steps failing = abort
                    result.ok = False
                    result.aborted_at = name
                    break
                # Later steps: continue with degraded flag
                result.ok = True  # degraded but not fatal

        result.summary = self._build_summary(result)
        console.print()
        console.print(f"[bold]{result.summary}[/]")

        # Step 10+: Notification (best-effort)
        self._notify(result.summary)

        return result

    def _preflight(self, platform_hints: list[str] | None = None) -> list[str]:
        """Step 0: Pre-flight checklist per test-coordinator.md."""
        missing = []
        import sys
        if sys.version_info < (3, 10):
            missing.append("Python 3.10+ required")
        if not _WORKSPACE.is_dir():
            missing.append(f"workspace directory not found: {_WORKSPACE}")

        hints = set(platform_hints or [])
        # Platform-specific checks from test-coordinator.md Step 0
        if "desktop_windows" in hints:
            if not os.environ.get("WIN_APP_PATH"):
                missing.append("WIN_APP_PATH (.env) — EXE完整路径")
            try:
                import pyautogui  # noqa: F401
            except ImportError:
                missing.append("pip install pyautogui (desktop test)")
        if "mobile_android" in hints or "mobile_ios" in hints:
            if not os.environ.get("ANDROID_HOME") and "android" in str(hints):
                missing.append("ANDROID_HOME (.env)")
        if "api" in hints or "web" in hints:
            if not os.environ.get("TEST_APP_URL"):
                missing.append("TEST_APP_URL (.env)")
        return missing

    def _detect_platform(self, target: str) -> list[str]:
        """Simple keyword-based platform detection for preflight checklist."""
        text = target.lower()
        hints = []
        if any(w in text for w in ("exe", "windows", "desktop", "win32", "pywinauto")):
            hints.append("desktop_windows")
        if any(w in text for w in ("android", "apk", "adb")):
            hints.append("mobile_android")
        if any(w in text for w in ("ios", "ipa", "xcode")):
            hints.append("mobile_ios")
        if any(w in text for w in ("api", "rest", "graphql", "endpoint", "http")):
            hints.append("api")
        if any(w in text for w in ("web", "browser", "playwright", "selenium", "page")):
            hints.append("web")
        if any(w in text for w in ("can", "automotive", "adas", "ota", "ecu")):
            hints.append("automotive")
        return hints

    def _print_checklist(self, platform_hints: list[str], missing: list[str]) -> None:
        """Print pre-flight checklist per test-coordinator.md Step 0."""
        from rich.panel import Panel
        detected = ", ".join(platform_hints) if platform_hints else "generic"
        lines = [f"Detected: {detected}", ""]
        lines.append("[bold]Required:[/]")
        for m in missing:
            lines.append(f"  [red]✗[/] {m}")
        lines.append("")
        lines.append("[dim]Fix missing items and re-run.[/]")
        console.print(Panel("\n".join(lines), title="Pre-flight Checklist", title_align="left"))

    def _load_prd(self, target: str) -> str | None:
        """Step 1: Load PRD via prd_loader per test-coordinator.md."""
        try:
            from utils.prd_loader import load_prd, suggest_agents
            text, meta = load_prd(target)
            if text:
                agents = suggest_agents(text)
                console.print(f"[dim]PRD loaded: {len(text)} chars, agents: {agents}[/]")
                return text[:5000]  # cap for LLM context
        except ImportError:
            pass
        except Exception:
            pass
        return None

    def _execute_with_retry(self, name: str, kind: str, target: str) -> dict[str, Any]:
        """Step 4 (env-manager): retry on failure per test-coordinator.md.
        Retry delays: 10s → 20s → 40s. Abort after 3 failures.
        """
        delays = [10, 20, 40]
        for attempt, delay in enumerate(delays, 1):
            outcome = self._execute_node(name, kind, target)
            if outcome.get("ok"):
                return outcome
            console.print(f"[yellow]retry {attempt}/{len(delays)} in {delay}s...[/]", end=" ")
            time.sleep(delay)
        console.print("[red]env-manager failed after 3 retries[/]")
        return {"ok": False, "stdout": "env-manager exhausted retries", "duration_ms": 0}

    def _notify(self, summary: str) -> None:
        """Post-pipeline notification per test-coordinator.md Step 10."""
        webhook = os.environ.get("TAGENT_NOTIFY_URL", "")
        if not webhook:
            return
        try:
            import requests
            requests.post(webhook, json={"text": summary}, timeout=5)
        except Exception:
            pass  # notification is best-effort

    def _route_target(self, target: str) -> str:
        """Quick routing: what does the router want for this target?"""
        try:
            from runtime.router.router import route as _route
            from runtime.router.schema import TargetArtifact

            artifact = TargetArtifact(kind="text", text=target, path="")
            decision = _route(artifact)
            names = [n.name for n in decision.dag[:5]]
            return " → ".join(names) if names else "no match"
        except Exception:
            return "routing skipped"

    def _execute_node(self, name: str, kind: str, target: str) -> dict[str, Any]:
        """Execute a single pipeline node via the orchestrator adapter."""
        try:
            from runtime.orchestrator.adapters.experts import execute_node

            t0 = time.time()
            outcome = execute_node(
                name=name,
                kind=kind,
                inputs={"target": target, "pipeline_step": name},
            )
            stdout = getattr(outcome, "stdout", "")
            result = {
                "ok": getattr(outcome, "ok", True),
                "stdout": stdout,
                "duration_ms": (time.time() - t0) * 1000,
            }
            # Extract structured metrics from test outputs for gate enforcement
            from runtime.orchestrator.metrics.parser import extract_metrics
            result["metrics"] = extract_metrics({"stdout": str(stdout)})
            return result
        except Exception as exc:
            return {"ok": False, "stdout": str(exc), "duration_ms": 0, "metrics": {}}

    def _check_gates(self, step_name: str, outcome: dict) -> str | None:
        """Check gate conditions after specific steps. Returns block reason or None."""
        metrics = outcome.get("metrics", {}) if isinstance(outcome, dict) else {}

        if step_name == "smoke-test":
            p0_total = metrics.get("p0_total", 0)
            p0_passed = metrics.get("p0_passed", 0)
            new_bugs = metrics.get("new_p0_bugs", 0)
            gate = check_smoke_gate(p0_total=p0_total, p0_passed=p0_passed, new_p0_bugs=new_bugs)
            if gate == GateResult.BLOCK:
                return f"P0 pass rate below 95% (or {new_bugs} new P0 bugs)"
        elif step_name == "test-executor":
            total = metrics.get("total", 0)
            passed = metrics.get("passed", 0)
            gate = check_regression_gate(total=total, passed=passed)
            if gate == GateResult.BLOCK:
                return "Regression pass rate below 90%"
            avg_ms = metrics.get("avg_response_ms", 0)
            p95_ms = metrics.get("p95_response_ms", 0)
            perf_gate = check_perf_gate(avg_response_ms=avg_ms, p95_response_ms=p95_ms)
            if perf_gate == GateResult.BLOCK:
                return "Performance thresholds exceeded"
        return None

    def _build_summary(self, result: PipelineResult) -> str:
        ok_count = sum(1 for s in result.steps if s.status == "ok")
        fail_count = sum(1 for s in result.steps if s.status == "failed")
        total = len(result.steps)
        status = "PASS" if result.ok and fail_count == 0 else "FAILED"
        if result.aborted_at:
            return f"{status} — {ok_count}/{total} steps ok, aborted at {result.aborted_at}"
        return f"{status} — {ok_count}/{total} steps completed"
