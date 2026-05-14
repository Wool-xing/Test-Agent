"""Real LLM-driven agent runners(V1.14.0-alpha · 主宪章 §33 + §40).

每个 runner 把 02-专家定义/*.md 的角色描述变成可执行的 LLM 调用:
- 读上游产物 → 拼 prompt → 调 LLM → 解析输出 → 落产物 → 给下游

6 核心 runner(V1.14 5 个 + V1.15 加 env-manager):
- requirements-analyst (V1.14)
- automation-engineer (V1.14)
- test-executor (V1.14)
- bug-manager (V1.14)
- test-lead (V1.14)
- env-manager (V1.15.0-alpha, ROADMAP rollout #1 落地 — minimum viable)

未实现的 10 个 expert 仍走 SCRIPT_MAP no-op 兜底(主宪章 §9 已有实现不破坏)。
"""

from runtime.orchestrator.agents.base import AGENT_RUNNERS, AgentRunner, RunnerContext, get_runner  # noqa: F401

# 触发注册(每个模块加载时 @register 注册到 AGENT_RUNNERS)
from runtime.orchestrator.agents import (  # noqa: F401,E402
    requirements_analyst,
    automation_engineer,
    test_executor,
    bug_manager,
    test_lead,
    env_manager,
)
