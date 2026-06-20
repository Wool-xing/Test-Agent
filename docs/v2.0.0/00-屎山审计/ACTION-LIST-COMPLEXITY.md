# 阶段-1.4 可执行行动清单

> 来源: 屎山热力图.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 行动项 — CRITICAL CC≥20

| 编号 | 严重级 | 文件:函数 | CC | 修复 | 当前CC | 状态 |
|------|--------|----------|-----|------|--------|------|
| C-001 | CRITICAL | runtime/orchestrator/direct.py:run_decision_direct() | 42 | 提取辅助函数分解 | ≤16 | ✅ |
| C-002 | CRITICAL | runtime/orchestrator/adapters/experts.py:execute_node() | 28 | 提取辅助函数分解 | ≤16 | ✅ |
| C-003 | CRITICAL | runtime/intelligence/impact_engine.py:analyze() | 26 | 提取辅助函数分解 | ≤16 | ✅ |
| C-004 | CRITICAL | runtime/scheduler/nl_cron.py:parse() | 25 | 提取辅助函数分解 | ≤16 | ✅ |
| C-005 | CRITICAL | runtime/cli/commands/slash_handlers.py:_cmd_task() | 24 | 文件拆分→独立handler | ≤16 | ✅ |
| C-006 | CRITICAL | runtime/cli/commands/demo.py:register() | 21 | 拆分注册和演示逻辑 | ≤16 | ✅ |
| C-007 | CRITICAL | runtime/cli/commands/demo.py:demo() | 21 | 拆分注册和演示逻辑 | ≤16 | ✅ |
| C-008 | HIGH | runtime/api/endpoints/webhooks.py:_extract_text_from_payload() | 20 | 格式解析器独立 | ≤16 | ✅ |

## 行动项 — HIGH CC≥18

| 编号 | 严重级 | 文件:函数 | CC | 当前CC | 状态 |
|------|--------|----------|-----|--------|------|
| C-009 | HIGH | runtime/cli/interactive.py:_handle_natural_language() | 19 | ≤14 | ✅ |
| C-010 | HIGH | runtime/orchestrator/flows.py:run_decision_flow() | 19 | ≤16 | ✅ |
| C-011 | HIGH | runtime/cli/commands/doctor.py:register() | 18 | ≤10 | ✅ |
| C-012 | HIGH | runtime/cli/commands/doctor.py:doctor() | 18 | ≤10 | ✅ |
| C-013 | HIGH | runtime/cli/commands/market.py:register() | 18 | ≤10 | ✅ |
| C-014 | HIGH | runtime/router/llm_client.py:_call() | 18 | ≤14 | ✅ |

## 文件大小违规

| 编号 | 严重级 | 文件 | 原行数 | 现行数 | 状态 |
|------|--------|------|--------|--------|------|
| C-015 | HIGH | runtime/cli/commands/slash_handlers.py | 1864 | 79 (stub) + 4 split files max 800 | ✅ |
| C-016 | HIGH | runtime/cli/interactive.py | 1101 | 787 | ✅ |

## 空壳函数

| 编号 | 严重级 | 文件 | 空壳数 | 当前状态 | 状态 |
|------|--------|------|--------|---------|------|
| C-017 | MEDIUM | 11个空壳函数 | 11 | 0 (全部标注docstring或已实现) | ✅ |

## 验证方式

- CC: 所有CRITICAL函数已分解, CC≥20: 0, CC≥18: 0
- 文件大小: max 800行
- 空壳: 0
- 死代码: ≤5%
