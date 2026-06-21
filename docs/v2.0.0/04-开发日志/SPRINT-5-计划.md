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
| 5.1 | E2E执行器 (Playwright) | ✅ | check_page() 浏览器自动化 |
| 5.2 | Cron调度验证 | ✅ | run_job/tick/run_forever 815行 |
| 5.3 | Visual测试 | ✅ | capture+compare PIL/numpy |
| 5.4 | Integration测试 | ✅ | check_api+check_db |
| 5.5 | Pentest验证 | ✅ | 5模块全部可导入 |

## 验收

- 🤖 每种测试类型3+示例+真实断言
- 🤖 tagent run e2e → Playwright执行
- 🤖 cron创建+触发+历史
- 🤖 visual截图对比
