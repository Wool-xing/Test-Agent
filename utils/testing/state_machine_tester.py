# SPDX-License-Identifier: MIT
# NOTE: state_machine_tester_v2.py is the enhanced version (FSM with guards, weights, random walk).
# This v1 provides simpler 0/1-switch + negative test generation.
"""
状态迁移测试（State Transition Testing）
被引用方：03-用例设计 agent / testcase-design skill
基于状态图自动生成 N-switch coverage 用例。
"""
import json
import logging
from itertools import product
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class StateMachine:
    """有限状态机 + 用例自动生成"""

    def __init__(self, name: str = "FSM"):
        self.name = name
        self.states: Set[str] = set()
        self.initial: Optional[str] = None
        self.finals: Set[str] = set()
        self.transitions: List[Tuple[str, str, str, str]] = []  # (from, event, guard, to)

    def add_state(self, state: str, initial: bool = False, final: bool = False):
        self.states.add(state)
        if initial:
            self.initial = state
        if final:
            self.finals.add(state)

    def add_transition(self, frm: str, event: str, to: str, guard: str = ""):
        self.transitions.append((frm, event, guard, to))
        self.states.add(frm)
        self.states.add(to)

    # ----- 0-switch（每条迁移）-----

    def gen_0switch(self) -> List[Dict]:
        """每条迁移生成 1 用例（最少覆盖）"""
        cases = []
        for i, (frm, event, guard, to) in enumerate(self.transitions, 1):
            cases.append({
                "id": f"TC-{self.name}-T{i:03d}",
                "name": f"{frm} --[{event}]--> {to}",
                "preconditions": [f"系统处于 {frm}"],
                "steps": [f"触发事件: {event}" + (f"（守卫: {guard}）" if guard else "")],
                "expected": f"系统进入 {to}",
                "guard": guard,
            })
        return cases

    # ----- 1-switch（连续两条迁移）-----

    def gen_1switch(self) -> List[Dict]:
        """连续 2 条迁移路径"""
        adj: Dict[str, List] = {}
        for frm, event, guard, to in self.transitions:
            adj.setdefault(frm, []).append((event, guard, to))

        cases = []
        idx = 1
        for s, outs in adj.items():
            for (e1, g1, t1), nexts in product(outs, [adj.get(t1, []) for _, _, t1 in outs]):
                for e2, g2, t2 in nexts:
                    cases.append({
                        "id": f"TC-{self.name}-1S-{idx:03d}",
                        "name": f"{s} -[{e1}]-> ? -[{e2}]-> {t2}",
                        "steps": [f"事件1: {e1}", f"事件2: {e2}"],
                        "expected": f"最终状态 {t2}",
                    })
                    idx += 1
        return cases

    # ----- 非法事件（错误推测）-----

    def gen_negative(self) -> List[Dict]:
        """每个状态下，未定义的事件应被拒绝"""
        all_events = {e for _, e, _, _ in self.transitions}
        valid_in_state: Dict[str, Set[str]] = {}
        for frm, e, _, _ in self.transitions:
            valid_in_state.setdefault(frm, set()).add(e)

        cases = []
        idx = 1
        for state in self.states:
            invalid = all_events - valid_in_state.get(state, set())
            for e in invalid:
                cases.append({
                    "id": f"TC-{self.name}-NEG-{idx:03d}",
                    "name": f"{state} 状态拒绝 {e} 事件",
                    "preconditions": [f"系统处于 {state}"],
                    "steps": [f"触发事件: {e}"],
                    "expected": "事件被拒绝（错误提示 / 状态不变）",
                })
                idx += 1
        return cases

    def export_all(self, output: str = "workspace/测试用例/state_machine_cases.json") -> str:
        cases = {
            "0-switch": self.gen_0switch(),
            "1-switch": self.gen_1switch(),
            "negative": self.gen_negative(),
        }
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
        return output


# ===== 示例：登录状态机 =====

def login_fsm() -> StateMachine:
    fsm = StateMachine("LOGIN")
    fsm.add_state("Logout", initial=True)
    fsm.add_state("Login")
    fsm.add_state("Locked", final=False)
    fsm.add_transition("Logout", "正确登录", "Login")
    fsm.add_transition("Logout", "5次错误", "Locked", guard="错误次数 == 5")
    fsm.add_transition("Login", "退出", "Logout")
    fsm.add_transition("Locked", "30分钟后", "Logout", guard="时间 > 30min")
    return fsm


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="状态机用例生成")
    parser.add_argument("--demo", action="store_true", help="运行登录状态机示例")
    parser.add_argument("--output", default="workspace/测试用例/state_machine_cases.json")
    args = parser.parse_args()
    if args.demo:
        fsm = login_fsm()
        path = fsm.export_all(args.output)
        print(f"已生成: {path}")
