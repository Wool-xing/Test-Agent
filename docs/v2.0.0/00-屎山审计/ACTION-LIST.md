# 阶段-1.1 可执行行动清单

> 来源: AUDIT-REPORT.md + 代码审计清单.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 行动项

| 编号 | 严重级 | 文件:行号 | 问题描述 | 修复方案 | 验证方式 | 状态 |
|------|--------|----------|---------|---------|---------|------|
| A-001 | CRITICAL | runtime/cli/commands/slash_handlers.py | 1864行超800行限制 | 按命令类型拆分为4文件 | wc -l ≤800 per file | ✅ |
| A-002 | CRITICAL | runtime/cli/interactive.py | 1101行超800行限制 | 提取UI函数到interactive_ui.py | wc -l ≤800 | ✅ |
| A-003 | CRITICAL | runtime/orchestrator/direct.py:117 | run_decision_direct() CC=42 | 提取辅助函数分解 | CC≤16 | ✅ |
| A-004 | CRITICAL | runtime/orchestrator/adapters/experts.py:260 | execute_node() CC=28 | 提取辅助函数分解 | CC≤16 | ✅ |
| A-005 | CRITICAL | runtime/intelligence/impact_engine.py:114 | analyze() CC=26 | 提取辅助函数分解 | CC≤16 | ✅ |
| A-006 | CRITICAL | runtime/scheduler/nl_cron.py:66 | parse() CC=25 | 提取辅助函数分解 | CC≤16 | ✅ |
| A-007 | CRITICAL | runtime/router/llm_client.py:105 | _call() CC=18 | 提取_resolve_model()+_try_cache() | CC≤14 | ✅ |
| A-008 | HIGH | runtime/orchestrator/skills/__init__.py | registry导入失败 'cannot import name registry' | 添加 registry = SKILL_RUNNERS | `from runtime.orchestrator.skills import registry` 成功 | ✅ |
| A-009 | HIGH | runtime/api/endpoints/webhooks.py:302 | Discord webhook URL硬编码 | 提取为常量 _DISCORD_WEBHOOK_BASE | 硬编码扫描0发现 | ✅ |
| A-010 | MEDIUM | runtime/backends/local.py | connect()+close() pass占位 | 添加docstring说明是合法no-op | 空壳扫描0发现 | ✅ |
| A-011 | MEDIUM | runtime/backends/docker.py | close() pass占位 | 已有注释说明 intentionally no-op | 空壳扫描0发现 | ✅ |
| A-012 | MEDIUM | runtime/backends/daytona.py | connect()+close() pass占位 | 添加docstring说明auto-hibernate | 空壳扫描0发现 | ✅ |
| A-013 | MEDIUM | runtime/backends/singularity.py | connect()+close() pass占位 | 添加docstring说明是合法no-op | 空壳扫描0发现 | ✅ |
| A-014 | MEDIUM | runtime/api/audit.py | 未使用导入 `time` | 验证: time 实际使用中, 保留 | audit需要time | ⏸️ |
| A-015 | MEDIUM | runtime/cli/cross_env.py | 未使用导入 `json` | 删除import json | grep确认无残留 | ✅ |
| A-016 | MEDIUM | runtime/cli/data_cleaner.py | 未使用导入 `os`, `shutil` | 删除import os, import shutil | grep确认无残留 | ✅ |
| A-017 | MEDIUM | runtime/config/settings.py | 未使用导入 `psycopg` | 验证: 实际使用中, 保留 | settings需要psycopg | ⏸️ |
| A-018 | MEDIUM | runtime/cli/doctor.py | 未使用导入 `mcp` | 验证: 实际使用中, 保留 | doctor需要mcp | ⏸️ |
| A-019 | MEDIUM | runtime/cli/readiness.py | 未使用导入 `os`, `runtime` | 删除import os; runtime实际使用 | grep确认无残留 | ✅ |
| A-020 | MEDIUM | runtime/cli/user_profile.py | 未使用导入 `json`, `time` | 删除import json; time实际使用 | grep确认无残留 | ✅ |
| A-021 | MEDIUM | runtime/cli/commands/serve.py | 未使用导入 `sys` | 删除import sys | grep确认无残留 | ✅ |
| A-022 | MEDIUM | runtime/learning/curator.py | 未使用导入 `json` | 删除import json | grep确认无残留 | ✅ |
| A-023 | MEDIUM | runtime/mcp/client.py | 未使用导入 `asyncio` | 删除import asyncio | grep确认无残留 | ✅ |
| A-024 | MEDIUM | runtime/observability/audit.py | 未使用导入 `os` | 删除import os | grep确认无残留 | ✅ |
| A-025 | MEDIUM | runtime/orchestrator/user_hooks.py | 未使用导入 `threading` | 删除import threading | grep确认无残留 | ✅ |
| A-026 | LOW | 42个图谱孤立节点 | 候选死代码待调查, 多为文档/stub | 随知识图谱迭代处理 | 死代码率≤5% | ⏸️ TD-001, Sprint 6 |

状态: ⬜待处理 / 🔧处理中 / ✅已验证 / ⏸️延期(附原因)
