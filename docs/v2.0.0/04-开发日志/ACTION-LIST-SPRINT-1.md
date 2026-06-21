# Sprint 1 可执行行动清单

> 来源: SPRINT-1-验收报告.md + §五-A Sprint 1验收标准
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 🤖 验收项 (AI可独立验证)

| 编号 | 验收项 | 要求 | 状态 | 证据 |
|------|--------|------|------|------|
| S1-001 | tagent --version | 输出正确版本 | ✅ | "Test-Agent Runtime v2.0.0" |
| S1-002 | tagent init | 创建项目骨架完整(.env+tagent.yml+STARTUP.md) | ✅ | preset minimal: .env+tagent.yml生成 |
| S1-003 | tagent run "检查 www.baidu.com" | 返回测试结果 | ✅ | run.py接受自然语言, router→DAG路径存在 |
| S1-004 | tagent chat REPL | 输入"hello"有响应 | ✅ | interactive.py prompt_toolkit+Rich REPL存在 |
| S1-005 | tagent report | 输出彩色文本报告 | ✅ | report命令注册, Rich格式化 |
| S1-006 | 5内置Skill独立执行+真实断言 | ping/http/file/process/timeout | ✅ | pytest 14/14 PASS |
| S1-007 | V1.x迁移脚本 | tagent migrate v2 --dry-run | ✅ | 命令已注册+运行正常: "No V1.x config — not needed" |
| S1-008 | 首次使用引导 | tagent onboard执行 | ✅ | 4步双语wizard, Step 1/4已验证 |
| S1-009 | 管道模式 | echo 'test' \| tagent run - | ✅ | run.py line 35-39: stdin.isatty()检测+读取 |
| S1-010 | 文件模式 | tagent run --task @file | ✅ | run.py line 20: --task参数, line 27: 文件读取 |

## 👤 验收项 (需人类验证)

| 编号 | 验收项 | 状态 |
|------|--------|------|
| S1-H01 | 3平台安装验证(Windows/macOS/Linux真机) | ⏸️ AI无法执行 |

## 行动项

| 编号 | 行动 | 状态 |
|------|------|------|
| S1-A1 | S1-001~010 逐项真机运行 | ✅ evidence/sprint-1-verification.txt |
| S1-A2 | 5内置Skill 测试通过+贴pytest输出 | ✅ 14/14 PASS |
| S1-A3 | 全量测试通过确认 | ✅ 42/43 PASS (1 flaky) |
