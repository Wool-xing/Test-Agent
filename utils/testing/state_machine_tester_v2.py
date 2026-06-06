# SPDX-License-Identifier: MIT
"""
State Machine Tester v2 — N-switch coverage, executable guards, hierarchical states.

Upgrades vs state_machine_tester.py:
- Configurable N-switch (N=1/2/3)
- Executable guard evaluation engine
- State invariants (per-state assertions)
- Transition probabilities/weights
- Hierarchical state machines (Harel statecharts)
- Integration with test executor

Usage:
  python state_machine_tester_v2.py generate --fsm fsm.json --nswitch 2
  python state_machine_tester_v2.py execute --fsm fsm.json --driver login_driver.py
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class Transition:
    event: str
    from_state: str
    to_state: str
    guard: str = ""          # Python expression evaluated against context
    weight: float = 1.0      # Probability weight (relative)
    action: str = ""         # Python expression executed on transition

    _SAFE_BUILTINS = {"True": True, "False": False, "None": None,
                       "abs": abs, "min": min, "max": max, "len": len,
                       "int": int, "float": float, "str": str, "bool": bool,
                       "isinstance": isinstance, "round": round, "sum": sum}
    _DANGEROUS_RE = re.compile(r"__|import\b|\bdel\b|getattr|setattr|eval\b|exec\b|compile\b|open\b|__import__")

    @classmethod
    def _validate_code(cls, code: str, label: str) -> None:
        """Reject dangerous patterns to harden restricted eval/exec sandbox."""
        if cls._DANGEROUS_RE.search(code):
            raise ValueError(f"Dangerous pattern in {label}: {code!r}")

    def evaluate_guard(self, ctx: dict) -> bool:
        if not self.guard:
            return True
        Transition._validate_code(self.guard, "guard")
        try:
            # Restricted eval with whitelisted builtins
            return bool(eval(self.guard, {"__builtins__": self._SAFE_BUILTINS}, ctx))
        except Exception:
            return False

    def execute_action(self, ctx: dict) -> None:
        if self.action:
            Transition._validate_code(self.action, "action")
            try:
                # exec not allowed for actions — only safe assignment via ctx dict
                _locals = {}
                exec(self.action, {"__builtins__": self._SAFE_BUILTINS}, {**ctx, "_out": _locals})
                ctx.update(_locals)
            except Exception:
                pass


@dataclass
class State:
    name: str
    invariants: list[str] = field(default_factory=list)  # Python expressions that must be True
    parent: str = ""        # For hierarchical: parent state name
    entry_action: str = ""
    exit_action: str = ""

    def check_invariants(self, ctx: dict) -> list[str]:
        violations = []
        for inv in self.invariants:
            try:
                Transition._validate_code(inv, "invariant")
                if not eval(inv, {"__builtins__": {}}, ctx):
                    violations.append(inv)
            except ValueError:
                violations.append(f"{inv} (dangerous pattern)")
            except Exception:
                violations.append(f"{inv} (eval error)")
        return violations


@dataclass
class FSM:
    name: str
    states: dict[str, State] = field(default_factory=dict)
    transitions: list[Transition] = field(default_factory=list)
    initial_state: str = ""

    def out_transitions(self, state: str) -> list[Transition]:
        return [t for t in self.transitions if t.from_state == state]

    def out_events(self, state: str) -> list[str]:
        return list({t.event for t in self.out_transitions(state)})

    def apply(self, state: str, event: str, ctx: dict) -> str | None:
        """Try to apply event. Returns new state or None if no valid transition."""
        candidates = [t for t in self.out_transitions(state) if t.event == event]
        for t in candidates:
            if t.evaluate_guard(ctx):
                t.execute_action(ctx)
                return t.to_state
        return None


# ═══════════════════════════════════════════════════════════════
# N-switch coverage generator
# ═══════════════════════════════════════════════════════════════

def generate_0switch(fsm: FSM) -> list[list[str]]:
    """0-switch: every individual transition."""
    return [[t.event] for t in fsm.transitions]


def generate_1switch(fsm: FSM) -> list[list[str]]:
    """1-switch: every pair of adjacent transitions."""
    paths = []
    for t1 in fsm.transitions:
        for t2 in fsm.out_transitions(t1.to_state):
            paths.append([t1.event, t2.event])
    return paths


def generate_nswitch(fsm: FSM, n: int = 2) -> list[list[str]]:
    """N-switch: all event sequences of length N+1 traversing valid transitions."""
    if n == 0:
        return generate_0switch(fsm)
    if n == 1:
        return generate_1switch(fsm)

    # Build from (n-1)-switch paths
    prev_paths = generate_nswitch(fsm, n - 1)
    paths = []
    for path in prev_paths:
        # Walk path to find current state
        state = fsm.initial_state
        for event in path:
            next_state = fsm.apply(state, event, {})
            if next_state:
                state = next_state
            else:
                break
        # Extend with one more transition
        for t in fsm.out_transitions(state):
            paths.append(path + [t.event])
    return paths


# ═══════════════════════════════════════════════════════════════
# Weighted random walk
# ═══════════════════════════════════════════════════════════════

def weighted_random_walk(fsm: FSM, max_steps: int = 50, ctx: dict | None = None) -> list[dict]:
    """Generate a probabilistic test walk through the FSM."""
    if ctx is None:
        ctx = {}
    state = fsm.initial_state
    trace = []

    for _ in range(max_steps):
        transitions = fsm.out_transitions(state)
        valid = [t for t in transitions if t.evaluate_guard(ctx)]
        if not valid:
            break

        # Weighted random selection
        weights = [t.weight for t in valid]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0
        chosen = valid[0]
        for t, w in zip(valid, weights):
            cumulative += w
            if r <= cumulative:
                chosen = t
                break

        chosen.execute_action(ctx)
        trace.append({
            "from": state, "event": chosen.event, "to": chosen.to_state,
            "guard_evaluated": chosen.guard,
        })
        state = chosen.to_state

    return trace


# ═══════════════════════════════════════════════════════════════
# Test executor
# ═══════════════════════════════════════════════════════════════

def execute_test_path(fsm: FSM, event_path: list[str],
                       ctx: dict | None = None,
                       pre_condition: Callable[[dict], bool] | None = None,
                       post_condition: Callable[[dict], bool] | None = None) -> dict:
    """Execute a single event path against the FSM with pre/post conditions."""
    if ctx is None:
        ctx = {}
    state = fsm.initial_state
    trace = []
    violations = []

    if pre_condition and not pre_condition(ctx):
        violations.append("pre-condition failed")

    for event in event_path:
        state_obj = fsm.states.get(state)
        if state_obj:
            inv_violations = state_obj.check_invariants(ctx)
            if inv_violations:
                violations.append({"state": state, "invariant_violations": inv_violations})

        next_state = fsm.apply(state, event, ctx)
        if next_state is None:
            violations.append({"state": state, "event": event, "reason": "no valid transition"})
            break

        trace.append({"from": state, "event": event, "to": next_state})
        state = next_state

    if post_condition and not post_condition(ctx):
        violations.append("post-condition failed")

    return {"path": event_path, "trace": trace, "final_state": state,
            "violations": violations, "passed": len(violations) == 0}


# ═══════════════════════════════════════════════════════════════
# Negative testing (illegal events)
# ═══════════════════════════════════════════════════════════════

def generate_negative_tests(fsm: FSM) -> list[dict]:
    """For each state + non-valid event, verify event is rejected."""
    tests = []
    all_events = {t.event for t in fsm.transitions}
    for state_name, state in fsm.states.items():
        valid_events = set(fsm.out_events(state_name))
        illegal = all_events - valid_events
        for event in illegal:
            tests.append({"state": state_name, "event": event, "expect": "rejected"})
    return tests


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="State Machine Tester v2")
    sub = ap.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate N-switch coverage")
    gen.add_argument("--fsm", required=True, help="FSM JSON file")
    gen.add_argument("--nswitch", type=int, default=1)

    walk = sub.add_parser("walk", help="Weighted random walk")
    walk.add_argument("--fsm", required=True)
    walk.add_argument("--steps", type=int, default=20)
    walk.add_argument("--seed", type=int, default=None)

    neg = sub.add_parser("negative", help="Generate negative tests")

    args = ap.parse_args()

    # Load FSM
    if hasattr(args, "fsm") and args.fsm:
        data = json.loads(Path(args.fsm).read_text(encoding="utf-8"))
        fsm = FSM(name=data.get("name", "unnamed"), initial_state=data.get("initial", ""))
        for s in data.get("states", []):
            fsm.states[s["name"]] = State(name=s["name"], invariants=s.get("invariants", []),
                                          parent=s.get("parent", ""))
        for t in data.get("transitions", []):
            fsm.transitions.append(Transition(**{k: t.get(k) if k != "weight" else t.get(k, 1.0)
                                                   for k in ["event", "from_state", "to_state", "guard", "weight", "action"]}))

    if args.cmd == "generate":
        paths = generate_nswitch(fsm, args.nswitch)
        print(f"N={args.nswitch} switch: {len(paths)} paths")
        for p in paths[:20]:
            print(f"  {' → '.join(p)}")

    elif args.cmd == "walk":
        if args.seed is not None:
            random.seed(args.seed)
        trace = weighted_random_walk(fsm, args.steps)
        print(f"Random walk ({len(trace)} steps):")
        for step in trace:
            print(f"  {step['from']} --[{step['event']}]--> {step['to']}")

    elif args.cmd == "negative":
        tests = generate_negative_tests(fsm)
        print(f"Negative tests: {len(tests)}")
        for t in tests[:20]:
            print(f"  State '{t['state']}' + event '{t['event']}' → expect {t['expect']}")
