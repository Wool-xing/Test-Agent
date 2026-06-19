---
name: ai-test
description: AI/ML 模型测试 Skill。模型质量 + 数据漂移 + 推理性能 + 公平性 + LLM 应用。底层调用 utils/ai_validator。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: script
---

# AI/ML 模型测试 Skill

## 触发方式

```text
/ai-test [子场景：model|drift|perf|fairness|llm]

```text

## 🔔 开测前准备清单（必看）

```text

□ 推理服务 endpoint → AI_INFERENCE_URL
□ LLM API URL + key → LLM_API_URL / LLM_API_KEY
□ 黄金测试集 CSV（含 input + label 列）→ AI_GOLDEN_TEST_SET
□ 模型版本号 → AI_MODEL_VERSION（Bug 报告 buildFound）
□ 漂移基线数据（可选）→ AI_DRIFT_BASELINE
□ 公平性测试集（含敏感属性列，如 gender / race）+ fairness_auditor.py 偏见审计
□ LLM 测试用例 yaml → workspace/自动化脚本/python/ai/prompts/llm_eval_cases.yaml

```text

## 适用场景

- 传统 ML 模型（分类 / 回归 / 排序）
- 深度学习模型（CV / NLP / 推荐）
- LLM 应用（聊天机器人 / 内容生成 / Agent）
- 推理服务（HTTP / gRPC / 离线批处理）

## 执行流程

```bash

# 模型质量

pytest -m "ai and model and p0" -v

# 数据漂移

pytest -m "ai and drift" -v

# 推理性能

pytest -m "ai and performance" -v

# 公平性

pytest -m "ai and fairness" -v

# LLM 应用

pytest -m "ai and llm" -v

```text

## 质量门禁（项目自定，默认参考）

| 指标 | 默认 |
| ------ | ------ |
| 准确率 | ≥0.90 |
| P95 延迟 | ≤200ms |
| 数据漂移（KS p） | >0.05 |
| 公平性差距 | <0.05 |
| LLM 格式合规率 | ≥95% |
| LLM 拒答率（有害） | ≥95% |

## 输出文件

```text

workspace/测试报告/{项目名}/
├── ai-eval/
├── ai-drift/
├── ai-fairness/
└── llm-cases/

```text
