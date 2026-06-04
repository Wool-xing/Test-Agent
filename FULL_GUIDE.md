# Test-Agent 完整指南（FULL_GUIDE）· 项目永久宪章

> **本文档定位**：`test-agent-team` 项目的**永久记忆宪章** —— 跨会话、跨人员、跨工具的唯一权威来源。
> 简明入口 → [README.md](README.md) ；按职责分类速查 → [00-项目导航.md](00-项目导航.md)。
> **维护原则**：决策入档、开放问题入档、不打脸的承诺才写。重大决策须更新「📋 开放问题」与「🗺️ 项目当前状态」两节。

**项目名称**：`Test-Agent`（内部代号 `test-agent-team`）
**当前阶段**：Phase 2 前期（V1.0.0 · 16 expert + 32/32 skill active (11 production + 5 script-backed) + 0 rollout + 0 vision）
**版本**：V1.0.0（详见 [VERSION](VERSION) + [CHANGELOG.md](CHANGELOG.md)）
**更新日期**：2026-06-04
**模型**：Claude 4.x 系列（Opus 4.7 / Sonnet 4.6 / Haiku 4.5，由 Claude Code 默认管理）

---

## 📑 拆分公告（W7-d 文档重构）

> 原 `FULL_GUIDE.md` 1252 行 → 7 子文件迁至 [`docs/charter/`](docs/charter/INDEX.md)。
> 本文件保留为索引入口（兼容旧链接），内容均已迁出。
> 详见 [docs/charter/INDEX.md](docs/charter/INDEX.md)。

| # | 子文件 | 含节 |
|---|---|---|
| 01 | [vision-dimensions](docs/charter/01-vision-dimensions.md) | 项目宪章 + 文档导航 + 维度全图（9 簇）+ 关键模块清单 + 核心特性 |
| 02 | [coverage-matrix](docs/charter/02-coverage-matrix.md) | 全链路覆盖矩阵（产品 / 协议 / 输入 三视角） |
| 03 | [agentchat-protocol](docs/charter/03-agentchat-protocol.md) | AgentChat 协作协议 + 关键决议摘要 + 放行决议 |
| 04 | [skills-bugtracker](docs/charter/04-skills-bugtracker.md) | Skills 自进化机制 + Bug Tracker 多适配器 |
| 05 | [install-deploy](docs/charter/05-install-deploy.md) | 按需安装 + 架构图 + 快速开始 + 工作流 + 技术栈 + 闭环 + 升级 + 协作 + 跨 AI |
| 06 | [test-architecture](docs/charter/06-test-architecture.md) | 测试架构深度 + 关键反问 + 开放问题 + 术语表 |
| 07 | [runtime-license](docs/charter/07-runtime-license.md) | V1.36.0 运行时层 + LICENSE / CHANGELOG / 项目当前状态 |

## 跨文件链接迁移指引

旧链接 `FULL_GUIDE.md#section-anchor` 仍然可用 (本文件保留兼容)，但建议新引用直接指向 `docs/charter/0X-xxx.md#anchor` 形式更稳定。

## 维护原则（强调）

- 决策入档 / 开放问题入档 / 不打脸的承诺才写
- 重大决策须更新「📋 开放问题」(06-test-architecture) 与「🗺️ 项目当前状态」(07-runtime-license) 两节
- 任何子文件改动同步更新 `docs/charter/INDEX.md` 行数列（若行数显著变化）
