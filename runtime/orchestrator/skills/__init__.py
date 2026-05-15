"""Real LLM-driven skill runners (V1.21.0-alpha · ROADMAP skill rollout 起点).

每个 runner 把 03-技能定义/*.md 的 skill 描述变成可执行的 LLM 调用:
- 读上游产物 → 拼 prompt → 调 LLM → 解析输出 → 落产物 → 给下游

skill runner 复用 agents/base.py 的 AgentRunner 抽象 + RunnerContext + RunnerResult
(skill 与 expert 接口 100% 同, 仅 registry 独立 SKILL_RUNNERS 区分路由)。

2 核心 runner (V1.21.0-alpha 起点 + V1.23.0-alpha):
- pentest-coordinator (V1.21.0-alpha, ROADMAP skill rollout #1 落地 — minimum viable;
  渗透流程主编排: LLM 读 PRD + 授权 + scope → 5 阶段并发计划 (recon / vuln / exploit
  / post-exploit / report) + 子 skill 调用顺序 + 授权前置检查 evidence)
- mobile-test (V1.23.0-alpha, ROADMAP skill rollout #2 落地 — minimum viable;
  移动端执行编排: LLM 读 PRD + 上游 mobile-tester 产物 → 6 阶段执行计划
  (设备就绪 / Appium / 用例批次 / 性能采集 / Monkey / 报告归档)
  + 质量门禁 + 跨平台并行策略)

剩余 14 rollout skill 走 SCRIPT_MAP fallback (主宪章 §9 已有实现保留)。
"""

from runtime.orchestrator.agents.base import (  # noqa: F401
    AgentRunner,
    RunnerContext,
    RunnerResult,
    SKILL_RUNNERS,
    get_skill_runner,
    register_skill,
)

# 触发注册 (每个模块加载时 @register_skill 注册到 SKILL_RUNNERS)
from runtime.orchestrator.skills import (  # noqa: F401,E402
    mobile_test,
    pentest_coordinator,
)
