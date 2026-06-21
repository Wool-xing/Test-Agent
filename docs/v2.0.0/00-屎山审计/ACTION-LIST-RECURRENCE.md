# 阶段-1.5 可执行行动清单

> 来源: 问题复发清单.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 高风险模块 (fix≥3次)

| 编号 | 严重级 | 模块 | Fix次数 | 根因 | 修复 | 回归测试 | 状态 |
|------|--------|------|---------|------|------|---------|------|
| R-001 | HIGH | runtime/cli/interactive.py | 7 | 1101行超大文件, 职责过多 | 已拆分至787行+interactive_ui.py 399行 | test_interactive_commands.py ✅ | ✅ |
| R-002 | HIGH | install.py | 5 | 安装脚本跨平台差异+依赖检测 | 已有平台检测逻辑 | 无独立回归测试 | ⚠️ |
| R-003 | HIGH | runtime/cli/skins.py | 4 | 皮肤/主题系统频繁调整 | 主题系统已稳定 | 无独立回归测试 | ⚠️ |
| R-004 | MEDIUM | runtime/router/llm_client.py | 3 | _call() CC=18过大 | 提取_resolve_model()+_try_cache() | 间接覆盖(router tests) | ✅ |
| R-005 | MEDIUM | runtime/orchestrator/flows.py | 3 | 流程编排逻辑复杂 | 架构稳定 | 间接覆盖(orchestrator tests) | ✅ |
| R-006 | MEDIUM | runtime/config/settings.py | 3 | 配置系统迭代 | 配置结构稳定 | 间接覆盖(config tests) | ✅ |
| R-007 | MEDIUM | runtime/cli/commands/slash_handlers.py | 3 | 1864行超大文件 | 已拆分为5文件 | 间接覆盖(handler tests) | ✅ |

## 行动项

| 编号 | 行动 | 状态 |
|------|------|------|
| R-A1 | install.py 回归测试 — 测试安装/卸载/升级路径 | ⏸️ Sprint 7范围(发布准备) |
| R-A2 | skins.py 回归测试 — 测试主题切换/自定义/持久化 | ⏸️ Sprint 2A范围(TUI全功能) |

## 根因总结

根因模式: 超大文件(interactive/slash_handlers) + 设计不稳定(skins/install)
修复策略: 拆分→≤800行 + 接口稳定化
预防: CI门禁 — 文件>800行阻断, CC≥20阻断
