"""GateRegistry — Centralized gate definition loader and evaluator.

Loads all gate YAML files from specs/gates/ and provides:
- get(name)     → Gate | None
- list_all()     → list[Gate]
- evaluate(name, metrics) → (passed: bool, messages: list[str])
"""

from __future__ import annotations

import operator as op
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class GateCheck:
    """A single check within a quality gate."""

    metric: str
    operator: str  # gte, lte, eq, lt, gt
    threshold: float
    unit: str = ""
    description: str = ""

    # Map operator strings to Python comparison functions
    _OP_MAP: dict[str, Any] = field(
        default_factory=lambda: {
            "gte": op.ge,
            "lte": op.le,
            "eq": op.eq,
            "lt": op.lt,
            "gt": op.gt,
        },
        repr=False,
    )

    def evaluate(self, actual: float) -> bool:
        """Evaluate this check against an actual metric value."""
        compare = self._OP_MAP.get(self.operator)
        if compare is None:
            raise ValueError(f"Unknown operator: {self.operator!r}")
        return compare(actual, self.threshold)


@dataclass
class Gate:
    """A named quality gate with one or more checks."""

    name: str
    description: str
    severity: str  # blocker | critical | warning
    checks: list[GateCheck] = field(default_factory=list)
    timeout_minutes: int = 30
    auto_apply: bool = False


# ── Registry ─────────────────────────────────────────────────────────────────


class GateRegistry:
    """Load and evaluate quality gates from YAML definitions.

    Usage:
        registry = GateRegistry(Path("specs/gates"))
        gate = registry.get("smoke-gate")
        passed, msgs = registry.evaluate("smoke-gate", {"p0_pass_rate": 98, ...})
    """

    def __init__(self, gates_dir: Path | None = None) -> None:
        """Load all gate YAML files from *gates_dir*.

        If *gates_dir* is None, defaults to the ``specs/gates/`` directory
        next to this module.
        """
        if gates_dir is None:
            gates_dir = Path(__file__).resolve().parent

        self.gates: dict[str, Gate] = {}
        yaml_files = sorted(gates_dir.glob("*.yaml"))
        for gf in yaml_files:
            g = self._load_gate(gf)
            self.gates[g.name] = g

    # ── Public API ───────────────────────────────────────────────────────

    def get(self, name: str) -> Gate | None:
        """Return the gate with *name*, or None if not found."""
        return self.gates.get(name)

    def list_all(self) -> list[Gate]:
        """Return all loaded gates."""
        return list(self.gates.values())

    def evaluate(self, gate_name: str, metrics: dict[str, float]) -> tuple[bool, list[str]]:
        """Evaluate a named gate against a dict of metric values.

        Returns ``(passed, messages)`` where *passed* is True only if every
        check in the gate evaluates successfully, and *messages* is a list of
        human-readable per-check results.
        """
        gate = self.gates.get(gate_name)
        if gate is None:
            return False, [f"Gate '{gate_name}' not found in registry"]

        all_pass = True
        messages: list[str] = []

        for check in gate.checks:
            if check.metric not in metrics:
                all_pass = False
                messages.append(
                    f"[{check.metric}] MISSING — metric not provided"
                )
                continue

            actual = metrics[check.metric]
            passed = check.evaluate(actual)

            unit_suffix = f" {check.unit}" if check.unit else ""
            op_symbol = _op_symbol(check.operator)

            if passed:
                messages.append(
                    f"[{check.metric}] PASS — actual={actual}{unit_suffix} "
                    f"{op_symbol} threshold={check.threshold}{unit_suffix}"
                )
            else:
                all_pass = False
                messages.append(
                    f"[{check.metric}] FAIL — actual={actual}{unit_suffix} "
                    f"{op_symbol} threshold={check.threshold}{unit_suffix}"
                )

        return all_pass, messages

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_gate(path: Path) -> Gate:
        """Parse a single gate YAML file into a Gate object."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"Gate file is empty: {path}")

        checks = []
        for c in data.get("checks", []):
            checks.append(
                GateCheck(
                    metric=c["metric"],
                    operator=c["operator"],
                    threshold=float(c["threshold"]),
                    unit=str(c.get("unit", "")),
                    description=str(c.get("description", "")),
                )
            )

        return Gate(
            name=data["name"],
            description=data.get("description", ""),
            severity=data.get("severity", "warning"),
            checks=checks,
            timeout_minutes=int(data.get("timeout_minutes", 30)),
            auto_apply=bool(data.get("auto_apply", False)),
        )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _op_symbol(op_str: str) -> str:
    """Return a display symbol for an operator string."""
    return {"gte": ">=", "lte": "<=", "eq": "==", "lt": "<", "gt": ">"}.get(
        op_str, op_str
    )
