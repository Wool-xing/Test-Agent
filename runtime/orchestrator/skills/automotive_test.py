"""automotive-test skill · 整车测试主编排 (V1.31.0 batch).

10 阶段: HARA+ASIL → 静态 MISRA → 单元 MC/DC → SIL/PIL → HIL → CAN → ADAS → OTA → 合规 → 报告
"""
from __future__ import annotations

from pathlib import Path

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("automotive-test")
class AutomotiveTest(AgentRunner):
    def system_prompt(self) -> str: return "你是 automotive-test 主编排 skill。10 阶段整车测试: HARA → ASIL → MISRA → MC/DC → SIL/PIL → HIL → CAN → ADAS → OTA → 合规审计。ISO 26262 + SOTIF + UN R155/R156 合规驱动。输出严格 JSON。"
    def user_prompt(self, ctx: RunnerContext) -> str:
        return f"## PRD\n```\n{ctx.artifact_text[:3000]}\n```\n\n## schema\n{{\n  \"project_name\":\"string\",\"run_id\":\"string\",\"vehicle_subsystem\":\"ECU|ADAS|IVI|V2X\",\"asil_level\":\"A|B|C|D\",\n  \"phases\":[{{\"phase\":1,\"name\":\"HARA+ASIL\",\"sub_skills\":[],\"estimated_hr\":4}}],\n  \"sub_skills\":[\"/automotive-can-bus-test\",\"/automotive-adas-scenario\",\"/automotive-ota-update-test\",\"/automotive-hil-loop-test\"],\n  \"outputs\":{{\"plan_dir\":\"workspace/automotive/\"}},\"risks\":[\"string\"],\"confidence\":\"string\"\n}}"
    def mock_output(self, ctx) -> dict: return {"project_name":"selftest","run_id":"016-000012","vehicle_subsystem":"ECU","asil_level":"C","phases":[{"phase":1,"name":"HARA+ASIL分解"},{"phase":2,"name":"MISRA静态分析"},{"phase":3,"name":"单元MC/DC"},{"phase":4,"name":"SIL/PIL集成"},{"phase":5,"name":"HIL真ECU"},{"phase":6,"name":"CAN总线"},{"phase":7,"name":"ADAS场景"},{"phase":8,"name":"OTA升级"},{"phase":9,"name":"合规审计"},{"phase":10,"name":"报告"}],"sub_skills":["/automotive-can-bus-test","/automotive-adas-scenario","/automotive-ota-update-test","/automotive-hil-loop-test"],"outputs":{"plan_dir":"workspace/automotive/"},"risks":["ASIL C/D 需 HIL 真 ECU,仿真不足"],"confidence":"medium","_mode":"mock"}
    def output_file(self, ctx) -> Path | None: return ctx.workspace / "automotive" / "plan.json"
    def summary(self, o) -> str: return f"车载主编排 {o.get('asil_level','?')} / {o.get('vehicle_subsystem','?')}"
