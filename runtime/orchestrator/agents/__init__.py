"""Real LLM-driven agent runners.

每个 runner 把 agents/*.md 的角色描述变成可执行的 LLM 调用:
- 读上游产物 → 拼 prompt → 调 LLM → 解析输出 → 落产物 → 给下游

11 核心 runner(所有 LLM-driven expert 已实装):
- requirements-analyst
- automation-engineer
- test-executor
- bug-manager
- test-lead
- env-manager (minimum viable)
- mobile-tester (minimum viable)
- visual-tester (minimum viable)
- system-tester (minimum viable)
- pentest-tester (minimum viable;
  仅输出测试计划文本, 不调外部攻击工具;真执行守护已在 utils 层 env gate)
- automotive-tester (minimum viable;
  ASIL 评估 + HIL 测试 + ADAS 场景 + OTA + 合规矩阵)

剩余 5 个 expert 走 SCRIPT_MAP script-backed (已有实现:
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
