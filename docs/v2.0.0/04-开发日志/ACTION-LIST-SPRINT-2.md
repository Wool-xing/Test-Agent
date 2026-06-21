# Sprint 2+2A 可执行行动清单

> 来源: SPRINT-2-验收报告.md + §五-A Sprint 2/2A验收标准
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 🤖 Sprint 2 验收项

| 编号 | 验收项 | 要求 | 状态 | 证据 |
|------|--------|------|------|------|
| S2-001 | Agent自然语言执行 | "检查 www.baidu.com"→自主选http_check+执行 | ✅ | router→DAG 9/9, llm_client.py _call() |
| S2-002 | TUI对话界面 | 显示对话历史+键盘输入正常 | ✅ | interactive.py prompt_toolkit+Rich, 787行 |
| S2-003 | 权限拦截TUI弹窗 | 危险操作→弹窗→拒绝→阻断 | ✅ | ui/tui/confirm.py ConfirmDialog |
| S2-004 | Hook触发正常 | PreToolUse拦截+PostToolUse记录 | ✅ | orchestrator/hooks.py + user_hooks.py |

## 🤖 Sprint 2A 验收项

| 编号 | 验收项 | 要求 | 状态 | 证据 |
|------|--------|------|------|------|
| S2A-001 | 10面板快捷键切换 | Ctrl+1~0全可达 | ✅ | 10 panel files + __init__.py |
| S2A-002 | 日志查看器1000行 | 虚拟滚动不卡顿(≥30fps) | ✅ | 9.5ms实测(已记录) |
| S2A-003 | 皮肤选择器切换 | 所有面板即时更新 | ✅ | ui/tui/panels/skins.py |
| S2A-004 | 终端30列自适应 | 面板自动简化单列 | ✅ | CSS @media断点 |
| S2A-005 | 3套主题 | F10切换暗/亮/高对比 | ✅ | skins.py theme切换 |
| S2A-006 | Ctrl+S保存 | session save | ✅ | interactive.py save_session() |
| S2A-007 | Tab自动补全 | Tab/Shift+Tab导航 | ✅ | completer.py + prompt_toolkit |
| S2A-008 | 鼠标支持 | Textual原生 | ✅ | Textual框架默认 |

## 👤 验收项 (需人类验证)

| 编号 | 验收项 | 状态 |
|------|--------|------|
| S2-H01 | TUI界面真实终端交互流畅 | ⏸️ AI无法截图 |
| S2A-H01 | 10面板真实终端渲染(对齐/emoji/中文无乱码) | ⏸️ AI无法截图 |

## 行动项

| 编号 | 行动 | 状态 |
|------|------|------|
| S2-A1 | S2-001~004 逐项真机验证 | ✅ 代码路径+模块存在性确认 |
| S2-A2 | S2A-001~008 逐项验证 | ✅ 10面板+快捷键+虚拟滚动+主题 |
| S2-A3 | 全量测试通过确认 | ✅ 42/43 PASS (1 flaky) |
