"""Tests for utils/testing/state_machine_tester_v2.py.

Locks the rule: a transition action that raises must NEVER look like an
executed transition — apply() rejects it and the walk records the error.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.testing.state_machine_tester_v2 import (  # noqa: E402
    FSM,
    State,
    Transition,
    execute_test_path,
    weighted_random_walk,
)


@pytest.fixture
def fsm_with_raising_action() -> FSM:
    """FSM whose only transition action raises ZeroDivisionError."""
    return FSM(
        name="boom",
        states={"idle": State(name="idle"), "done": State(name="done")},
        transitions=[
            Transition(from_state="idle", to_state="done", event="go", action="1/0"),
        ],
        initial_state="idle",
    )


@pytest.fixture
def fsm_with_valid_action() -> FSM:
    """FSM with a working action that writes into ctx."""
    return FSM(
        name="ok",
        states={"idle": State(name="idle"), "done": State(name="done")},
        transitions=[
            Transition(from_state="idle", to_state="done", event="go", action="_out[\"x\"] = 42"),
        ],
        initial_state="idle",
    )


class TestActionFailureNotSilent:
    def test_apply_rejects_transition_when_action_raises(self, fsm_with_raising_action):
        """apply() must return None, not the target state, when the action raises."""
        assert fsm_with_raising_action.apply("idle", "go", {}) is None

    def test_walk_records_action_error(self, fsm_with_raising_action):
        """weighted_random_walk must record the action error in the trace entry."""
        trace = weighted_random_walk(fsm_with_raising_action, max_steps=3)
        assert trace, "expected at least one trace entry"
        assert trace[0].get("action_error"), "action error must be recorded"

    def test_execute_path_reports_violation(self, fsm_with_raising_action):
        """execute_test_path must report passed=False with a violation."""
        result = execute_test_path(fsm_with_raising_action, ["go"])
        assert result["passed"] is False
        assert result["violations"], "expected at least one violation"


class TestActionSuccessStillWorks:
    def test_apply_executes_action_and_advances(self, fsm_with_valid_action):
        ctx: dict = {}
        assert fsm_with_valid_action.apply("idle", "go", ctx) == "done"
        assert ctx.get("x") == 42

    def test_execute_path_passes(self, fsm_with_valid_action):
        result = execute_test_path(fsm_with_valid_action, ["go"])
        assert result["passed"] is True
        assert result["final_state"] == "done"
