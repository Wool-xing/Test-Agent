---
name: eval-harness
description: Eval 框架 Skill。LLM/AI 系统评测:pass@k / Jaccard@k / top-1 stability / latency Δ。融合 gbrain eval 回放 + ECC eval-harness。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# eval-harness

## 触发

- LLM 应用迭代前后对比
- RAG 系统 retrieval 质量评测
- AI agent 路由准确率验证
- Prompt 版本回归

## 4 维度评测

| 指标 | 用途 |
| ------ | ------ |
|**Jaccard@k**| 检索集合相似度(本项目 router retrieval 用) |
|**top-1 stability**| 改动后 top-1 是否稳定 |
|**latency Δ**| 延迟变化 |
|**pass@k**| k 次采样中通过的比例(代码生成评测) |

## 本项目实现

-**runtime/tutor/eval_replay.py**(M5 已 ship): capture + replay + 3 指标
-**runtime/tests/test_router_real.py**(M2-7 已 ship):20 样本 + 单模型 ≥85% / 双投票 ≥95%
- LongMemEval-style 公共 benchmark(M8 路线)

## 使用

```bash
# 1. opt-in capture

TAGENT_EVAL_CAPTURE=1 tagent run "..."

# 2. 改 router/prompt/KB

# 3. replay 测改动影响

python -m runtime.tutor.eval_replay  # 输出 3 指标

```text

## 评测原则

-**opt-in 不偷数据**:`TAGENT_EVAL_CAPTURE=1` 必显式
-**PII 必 scrub**:落档前 6 类正则
-**off-by-default**:production 用户**不**意外累积
-**失败必复现**:固定 seed + snapshot

## 不做

- 不静默 capture(必 opt-in)
- 不 leak 原始 query(scrub)
- 不只看 mean(必看分布 P50/P95/P99)
