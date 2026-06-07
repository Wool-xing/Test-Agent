---
name: agent-introspection-debugging
description: "Agent 自省调试 Skill。LLM 决策 / 工具调用 / 上下文 / token / 状态机透明化。失败用例分析 + 决策回放。派生自 ECC 同名 skill(主宪章 §28)。"
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# agent-introspection-debugging

## 触发

- Agent 行为奇怪(过度调用 / 卡死 / 输出乱)
- 路由决策错误调试(对应 §M2-7 router 真模型测试失败)
- token 消耗异常
- 上下文丢失 / 污染

## 5 维度自省

| 维 | 工具 |
|----|------|
| **决策回放** | `workspace/测试报告/{项目名}/decisions/` JSON 时间序 |
| **工具调用** | OTel span(`runtime/observability/otel.py`)+ Loguru |
| **token 消耗** | LLM provider header + LiteLLM 记账 |
| **上下文** | prompt 长度 + 截断点 + 主-子 session 隔离审查 |
| **状态机** | Prefect flow run state(`runtime/orchestrator/flows.py`)|

## 决策回放(主宪章 §18-12 满足)

每次 routing / curator / scheduler 决策已自动落 `decisions/{date}_{tool}_{run_id}.json`。
含:输入快照 + 模型版本 + 阈值 + 判断结论 + 理由。

调试流:
1. 找 run_id
2. cat `decisions/*_<run_id>.json`
3. 看 LLM 看到的输入(input snapshot)+ 给的输出(decision)
4. 对比是否符合预期

## 工具调用 trace

OTel 启用时:
```
flow.run                      # api.request 总 span
├─ router.decide              # LLM 决策
│  ├─ llm.call provider=claude
│  └─ catalog.lookup
└─ orchestrator.flow_run
   ├─ task.requirements-analyst
   └─ task.testcase-designer ...
```

## token 异常诊断

- 单 LLM call > 10k tokens → 输入太大(catalog 没裁?)
- 主-子 session 共享 cache → §22 子代理 aux_client 隔离失效
- 重复调相同 LLM(无 cache)→ Anthropic prompt cache 没设 ttl

## 与主宪章融合

- §18-12 决策可追溯(本 skill 直接消费)
- §22 隔离 client(本 skill 检测违反)
- §21 横切可复现性(本 skill 必带 seed + snapshot)

## 不做

- 不只看 LLM 输出(必看输入 + token + 上下文)
- 不靠 print 调试(必走 OTel + Loguru 结构化)
- 不删 decisions/(主宪章 §1+§18-16 不可删)
