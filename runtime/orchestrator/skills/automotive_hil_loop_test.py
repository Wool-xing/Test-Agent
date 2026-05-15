"""automotive-hil-loop-test · HIL/SIL/MIL/PIL 环路编排 (V1.31.0-alpha)."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill

@register_skill("automotive-hil-loop-test")
class AutomotiveHilLoopTest(AgentRunner):
    def system_prompt(self) -> str: return "你是 automotive-hil-loop-test skill。MIL/SIL/PIL/HIL 4 环编排。ASIL C/D 必经 HIL(真 ECU+I/O)。故障注入 + 极端工况。输出严格 JSON。"
    def user_prompt(self, ctx: RunnerContext) -> str:
        return f"## PRD\n```\n{ctx.artifact_text[:3000]}\n```\n\n## schema\n{{\n  \"project_name\":\"string\",\"run_id\":\"string\",\n  \"loops\":[\"MIL\",\"SIL\",\"PIL\",\"HIL\"],\n  \"asil_required\":\"C|D\",\n  \"fault_injection\":true,\n  \"platform\":\"dSPACE|NI|ETAS|Vector\",\n  \"outputs\":{{\"hil_dir\":\"workspace/automotive/hil/\"}},\"risks\":[\"string\"],\"confidence\":\"string\"\n}}"
    def mock_output(self, ctx) -> dict: return {"project_name":"selftest","run_id":"016-000016","loops":["MIL","SIL","HIL"],"asil_required":"C","fault_injection":True,"platform":"dSPACE","outputs":{"hil_dir":"workspace/automotive/hil/"},"risks":["HIL 真 ECU 断连致测试中断"],"confidence":"medium","_mode":"mock"}
    def output_file(self, ctx) -> Path | None: return ctx.workspace / "automotive" / "hil_plan.json"
    def summary(self, o) -> str: return f"HIL {len(o.get('loops',[]))} 环 / ASIL={o.get('asil_required','?')}"
