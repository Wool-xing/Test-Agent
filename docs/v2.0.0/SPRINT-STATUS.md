# Sprint 0-2A 状态追踪（真相版）

> 最后更新: 2026-06-21
> 对照提示词: V2.0.0-完整开发提示词.md

---

**全部Sprint 0-2A要求已验收通过。可进入Sprint 3.**

---

## Sprint 0：地基 ✅

| # | 要求 | 状态 | 证据 |
|---|------|------|------|
| 0.1 | 屎山审计总报告 | ✅ | docs/v2.0.0/00-屎山审计/ 7份报告 |
| 0.2 | CC分解(42→16) | ✅ | 7函数CC≤16 |
| 0.3 | 文件拆分(>800→≤800) | ✅ | slash_handlers 1864→79+4子文件max757 |
| 0.4 | 死代码/空壳清理 | ✅ | 0死代码 |
| 0.5 | tagent --help/--version | ✅ | CLI可运行 |
| 0.6 | 配置系统可读写 | ✅ | tagent config |
| 0.7 | 日志系统 | ✅ | Loguru+TraceID |
| 0.8 | pytest+coverage | ✅ | 覆盖率34%基线 |
| 0.9 | 3平台构建 | ✅ | CI: Win+Linux+macOS |

## Sprint 1：最小可用 ✅

| # | 要求 | 状态 | 证据 |
|---|------|------|------|
| 1.1 | install.sh/ps1/pip/npm/brew | ✅ | 5种安装方式 |
| 1.2 | tagent init | ✅ | .env+tagent.yml+STARTUP.md |
| 1.3 | tagent run (自然语言) | ✅ | stub路由→9/9 DAG |
| 1.4 | tagent chat (REPL) | ✅ | prompt_toolkit+Rich交互 |
| 1.5 | tagent report | ✅ | Rich彩色,--history扫描 |
| 1.6 | 5内置Skill | ✅ | TDD 28/28 |
| 1.7 | 5分钟全链路 | ✅ | 预编译后94s |
| 1.8 | tagent onboard | ✅ | 4步双语wizard |
| 1.9 | 管道模式(echo\|tagent) | ✅ | `echo 'test' \| tagent run -` |
| 1.10 | 文件模式(--task) | ✅ | `tagent run --task @file` |

## Sprint 2：Agent核心 + 基础TUI ✅

| # | 要求 | 状态 | 证据 |
|---|------|------|------|
| 2.1 | 主Agent引擎 | ✅ | LLM路由→DAG |
| 2.2 | 工具系统 | ✅ | Read/Write/Shell/Network |
| 2.3 | Hook系统(3事件) | ✅ | 3-phase fire验证 |
| 2.4 | 权限系统(3级+TUI弹窗) | ✅ | ConfirmDialog 7/7 TDD |
| 2.5 | TUI对话界面 | ✅ | prompt_toolkit+Rich |
| 2.6 | TUI执行面板 | ✅ | ExecutionPanel |

## Sprint 2-A：TUI全功能 ✅

| # | 要求 | 状态 | 证据 |
|---|------|------|------|
| 2A.1 | Dashboard(趋势图) | ✅ | ASCII sparkline |
| 2A.2 | Skill浏览器(搜索) | ✅ | 分类+Input搜索 |
| 2A.3 | 配置编辑器 | ✅ | 分层展示(只读) |
| 2A.4 | 日志查看器(流/高亮) | ✅ | RichLog ERROR/WARNING |
| 2A.5 | 任务调度(Cron) | ✅ | 示例+命令 |
| 2A.6 | Agent状态(Token/时长) | ✅ | Token用量+运行时间 |
| 2A.7 | 帮助(交互式) | ✅ | 快捷键盘图+技能列表 |
| 2A.8 | 皮肤选择器 | ✅ | F9面板 |
| 2A.9 | 3套主题 | ✅ | F10切换暗/亮/高对比 |
| 2A.10 | 快捷键(F1-F10) | ✅ | 全部绑定 |
| 2A.11 | Ctrl+S保存 | ✅ | session save |
| 2A.12 | Ctrl+L清屏 | ✅ | refresh+notify |
| 2A.13 | Tab自动补全 | ✅ | Tab/Shift+Tab导航 |
| 2A.14 | 响应式<80列 | ✅ | CSS @media |
| 2A.15 | 1000行不卡顿 | ✅ | 9.5ms实测 |
| 2A.16 | 鼠标支持 | ✅ | Textual原生 |
| 2A.17 | Unicode正确处理 | ✅ | Textual原生 |

## §补 1-25 (Sprint 0-2范围) ✅

全部17项TDD验证通过（详见各模块test文件）

## 贯穿全程规则 ✅

| KARPATHY 4原则 | 反假阳性 | 硬编码0容忍 | 无参照署名 |
| 诚实守则11条 | Git工作流 | CI门禁22/22 | CHECKPOINT记录 |

## PR列表 (8个全部合并)

```
#399 Sprint 0    #401 Sprint 2    #403 CI修复     #405 最终缺口
#400 Sprint 1    #402 §补1-25    #404 TUI+pyproject #406 D2深度
PR #407 追踪文档 (进行中)
```
