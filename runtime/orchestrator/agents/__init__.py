"""Real LLM-driven agent runners(V1.36.0 · 主宪章 §33 + §40).

每个 runner 把 agents/*.md 的角色描述变成可执行的 LLM 调用:
- 读上游产物 → 拼 prompt → 调 LLM → 解析输出 → 落产物 → 给下游

11 核心 runner(V1.x rollout 收尾,所有 LLM-driven expert 已实装):
- requirements-analyst (V1.14)
- automation-engineer (V1.14)
- test-executor (V1.14)
- bug-manager (V1.14)
- test-lead (V1.14)
- env-manager (V1.15.0, ROADMAP rollout #1 落地 — minimum viable)
- mobile-tester (V1.16.0, ROADMAP rollout #2 落地 — minimum viable)
- visual-tester (V1.17.0, ROADMAP rollout #3 落地 — minimum viable)
- system-tester (V1.18.0, ROADMAP rollout #4 落地 — minimum viable)
- pentest-tester (V1.19.0, ROADMAP rollout #5 落地 — minimum viable;
  仅输出测试计划文本, 不调外部攻击工具;真执行守护已在 utils 层 env gate)
- automotive-tester (V1.20.0, ROADMAP rollout #6 落地 — minimum viable;
  V1.x rollout 收尾;ASIL 评估 + HIL 测试 + ADAS 场景 + OTA + 合规矩阵)

剩余 5 个 expert 走 SCRIPT_MAP script-backed (主宪章 §9 已有实现:
testcase-designer / data-preparer / report-generator / desktop-tester / ai-tester)。
"""

# 触发注册(每个模块加载时 @register 注册到 AGENT_RUNNERS)
from runtime.orchestrator.agents import (  # noqa: F401,E402
    automation_engineer,
    automotive_tester,
    bug_manager,
    env_manager,
    mobile_tester,
    pentest_tester,
    requirements_analyst,
    system_tester,
    test_executor,
    test_lead,
    visual_tester,
)
from runtime.orchestrator.agents.base import (  # noqa: F401
    AGENT_RUNNERS,
    AgentRunner,
    RunnerContext,
    get_runner,
)
