# Sprint 5 计划 — 测试能力全覆盖

> 日期: 2026-06-21
> 协议: §五-A Sprint 5 (Week 6-7)
> 状态: 🔧 执行中

## 现有基础

| 功能 | 模块 | 行数 | 状态 |
|------|------|------|------|
| Cron调度 | runtime/scheduler/ | 815行 | ✅ 待验证 |
| Pentest | runtime/orchestrator/skills/pentest_*.py | 7文件 | ✅ 已有点 |
| E2E | 无 | - | ❌ 需新建 |
| Visual | 无 | - | ❌ 需新建 |
| Integration | 部分(API tests) | - | ⚠️ |

## 任务

| # | 功能 | TDD | 预计 |
|---|------|-----|------|
| 5.1 | E2E执行器 (Playwright) | ⬜ | tagent run e2e |
| 5.2 | Cron调度验证+增强 | ⬜ | 定时任务创建/触发/历史 |
| 5.3 | Visual测试 (screenshot compare) | ⬜ | 截图对比 |
| 5.4 | Integration测试执行器 | ⬜ | API/DB |

## 验收

- 🤖 每种测试类型3+示例+真实断言
- 🤖 tagent run e2e → Playwright执行
- 🤖 cron创建+触发+历史
- 🤖 visual截图对比
