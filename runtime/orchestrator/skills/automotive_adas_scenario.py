"""automotive-adas-scenario · ADAS 场景库测试编排."""
from __future__ import annotations

from pathlib import Path

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("automotive-adas-scenario")
class AutomotiveAdasScenario(AgentRunner):
    def system_prompt(self) -> str: return "你是 automotive-adas-scenario skill。AEB/ACC/LKA/APA/AVP/NOA 场景库编排。ODD 边界 + SOTIF ISO 21448 合规。输出严格 JSON。"
    def user_prompt(self, ctx: RunnerContext) -> str:
        return f"## PRD\n```\n{ctx.artifact_text[:3000]}\n```\n\n## schema\n{{\n  \"project_name\":\"string\",\"run_id\":\"string\",\n  \"categories\":[\"AEB\",\"ACC\",\"LKA\",\"APA\",\"AVP\",\"NOA\"],\n  \"odd_levels\":[\"in\",\"edge\",\"out\"],\n  \"simulation\":\"VTD|CarMaker|CARLA\",\n  \"outputs\":{{\"adas_dir\":\"workspace/automotive/adas/\"}},\"risks\":[\"string\"],\"confidence\":\"string\"\n}}"
    def mock_output(self, ctx) -> dict: return {"project_name":"selftest","run_id":"016-000014","categories":["AEB","ACC","LKA"],"odd_levels":["in","edge"],"simulation":"CARLA","outputs":{"adas_dir":"workspace/automotive/adas/"},"risks":["仿真物理参数偏差致 false negative"],"confidence":"medium","_mode":"mock"}
    def output_file(self, ctx) -> Path | None: return ctx.workspace / "automotive" / "adas_plan.json"
    def summary(self, o) -> str: return f"ADAS {len(o.get('categories',[]))} 类 / ODD={o.get('odd_levels',[])}"
