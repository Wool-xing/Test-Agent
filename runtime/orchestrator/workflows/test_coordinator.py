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
        """Execute the full pipeline. Returns PipelineResult with step details."""
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

        # Phase 0: Pre-flight
        missing = self._preflight()
        if missing:
            console.print(f"[red]Pre-flight failed: {', '.join(missing)}[/]")
            result.ok = False
            result.aborted_at = "preflight"
            result.summary = f"Missing: {', '.join(missing)}"
            return result

        # Phase 1: PRD load + route
        routing = self._route_target(target)
        console.print(f"[dim]Router → {routing}[/dim]")

        # Execute each step
        for i, (name, kind) in enumerate(self.SEQUENCE, 1):
            step = PipelineStep(name=name, kind=kind)
            result.steps.append(step)

            console.print(f"  [{i}/{len(self.SEQUENCE)}] {name}...", end=" ")
            try:
                outcome = self._execute_node(name, kind, target)
                step.status = "ok" if outcome.get("ok", True) else "failed"
                step.output = str(outcome.get("stdout", ""))[:200]
                step.duration_ms = outcome.get("duration_ms", 0)
                console.print(
                    f"[green]OK[/] ({step.duration_ms:.0f}ms)"
                    if step.status == "ok"
                    else f"[red]FAILED[/]"
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
        return result

    def _preflight(self) -> list[str]:
        """Check required env vars and tools. Returns list of missing items."""
        missing = []
        # Check Python version
        import sys
        if sys.version_info < (3, 10):
            missing.append("Python 3.10+ required")
        # Check workspace exists
        if not _WORKSPACE.is_dir():
            missing.append(f"workspace directory not found: {_WORKSPACE}")
        return missing

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
                run_id=f"tc-{int(t0)}",
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
