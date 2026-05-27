"""AgentRunner ABC + RunnerContext + registry."""

from __future__ import annotations

import abc
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass(slots=True)
class RunnerContext:
    """每节点跑前由 adapter 注入,带 PRD + 上游产物 + 配置."""

    artifact_text: str = ""        # 原始 PRD / target 内容(parsers 给的)
    upstream: dict[str, Any] = field(default_factory=dict)   # 上游 expert 产物 by name (RunnerResult.output)
    upstream_meta: dict[str, dict[str, Any]] = field(default_factory=dict)  # 上游元信息 by name
                                                                            # {ok: bool, degraded: bool, error: str}
                                                                            # test-lead 应检查任一 upstream_meta[*].degraded
                                                                            # → verdict 降级 conditional 而非 go
    settings_provider: str = ""    # 当前 LLM provider(stub 时走 mock)
    workspace: Path = field(default_factory=lambda: Path("workspace"))
    lang: str = "zh"
    mode: str = "exec"             # exec | learn | mock


@dataclass(slots=True)
class RunnerResult:
    """每节点跑完产出统一格式,落产物 + 给下游."""

    name: str
    ok: bool
    output: dict[str, Any]         # 结构化产物(per-agent schema)
    artifact_path: Path | None = None   # 写盘位置(可空)
    summary: str = ""              # 一行业务语言摘要(给 test-lead / report)
    duration_ms: int = 0
    raw_llm_response: str = ""     # debug / learn 模式给用户看
    error: str = ""
    degraded: bool = False         # True = mock 兜底 / LLM 失败 fallback / JSON 解析错,非真 LLM 输出
                                   # test-lead 看到任一 degraded → 上线决策不应输出 GO


class AgentRunner(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def system_prompt(self) -> str:
        """从 agents/*.md 提炼的角色 prompt."""

    @abc.abstractmethod
    def user_prompt(self, ctx: RunnerContext) -> str:
        """拼上游产物 + PRD 为单个 user message."""

    @abc.abstractmethod
    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        """stub provider 时返回的 schema-correct mock,让 selftest 不破."""

    def output_file(self, ctx: RunnerContext) -> Path | None:
        """覆盖此方法把 output 写盘;返回 None 不落盘."""
        return None

    def summary(self, output: dict[str, Any]) -> str:  # noqa: ARG002
        return ""

    def run(self, ctx: RunnerContext) -> RunnerResult:
        """
        执行 LLM-driven agent。ok/degraded 语义:
        - stub/mock 模式: ok=True + degraded=True (mock 兜底,主宪章 §33 selftest 允许)
        - 真 LLM 成功 + JSON 解析 OK: ok=True + degraded=False (真输出)
        - 真 LLM 成功但 JSON 解析错: ok=False + degraded=True (LLM 回了但不合规)
        - exec 模式 LLM 失败 fallback: ok=False + degraded=True (不再假绿)

        test-lead 看到任一上游 degraded → "上线决策"不应输出 GO,改 conditional 或 no-go。
        """
        t0 = time.time()
        degraded = False
        error_msg = ""

        if ctx.settings_provider == "stub" or ctx.mode == "mock":
            # stub/mock 模式: 输出 mock,标 degraded
            output = self.mock_output(ctx)
            raw = "[stub] mock output(主宪章 §33 selftest 兜底)"
            ok = True
            degraded = True
        else:
            try:
                from runtime.subagent.aux_client import aux_client

                client = aux_client()
                from runtime.config.settings import get_settings

                raw = client.complete(
                    self.system_prompt(),
                    self.user_prompt(ctx),
                    temperature=0.1,
                    max_tokens=get_settings().agent_max_tokens,
                )
                output = self._parse_json(raw)
                # JSON 解析错误 → ok=False + degraded
                if "_parse_error" in output:
                    ok = False
                    degraded = True
                    error_msg = output.get("_parse_error", "JSON parse failed")
                else:
                    ok = True
                    degraded = False
            except Exception as e:  # noqa: BLE001
                # exec 模式 LLM 失败 → fallback to mock 但**绝不假绿**: ok=False + degraded=True
                logger.error("{} runner LLM failed: {}; degraded fallback", self.name, e)
                output = self.mock_output(ctx)
                raw = f"[fallback] LLM raised: {e}"
                ok = False
                degraded = True
                error_msg = f"LLM call failed: {e}"

        # 落盘(可选)
        artifact_path = self.output_file(ctx)
        if artifact_path is not None:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

        return RunnerResult(
            name=self.name,
            ok=ok,
            output=output,
            artifact_path=artifact_path,
            summary=self.summary(output),
            duration_ms=int((time.time() - t0) * 1000),
            raw_llm_response=raw[:2000],
            error=error_msg,
            degraded=degraded,
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw[3:-3].strip() if raw.endswith("```") else raw[3:]
            if "\n" in raw:
                _, raw = raw.split("\n", 1)
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < 0:
            return {"_raw": raw[:500], "_parse_error": "no JSON object found"}
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError as e:
            return {"_raw": raw[:500], "_parse_error": str(e)}


AGENT_RUNNERS: dict[str, type[AgentRunner]] = {}


def register(name: str):
    def deco(cls: type[AgentRunner]):
        cls.name = name
        AGENT_RUNNERS[name] = cls
        return cls

    return deco


def get_runner(name: str) -> AgentRunner | None:
    cls = AGENT_RUNNERS.get(name)
    return cls() if cls else None


# Skill runner registry (V1.21.0 — skill LLM-driven rollout 基础设施).
# SkillRunner 接口与 AgentRunner 100% 一致 (system_prompt / user_prompt /
# mock_output / summary / output_file / run), 仅 registry 独立, 避免 expert/skill
# 同名冲突,且让 catalog / router / orchestrator 按 kind 路由清晰。
SKILL_RUNNERS: dict[str, type[AgentRunner]] = {}


def register_skill(name: str):
    def deco(cls: type[AgentRunner]):
        cls.name = name
        SKILL_RUNNERS[name] = cls
        return cls

    return deco


def get_skill_runner(name: str) -> AgentRunner | None:
    cls = SKILL_RUNNERS.get(name)
    return cls() if cls else None
