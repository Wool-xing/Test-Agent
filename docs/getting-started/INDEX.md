# docs/getting-started 索引

> 顶层导航见根目录 `00-项目导航.md`；完整详细文档见根目录 `FULL_GUIDE.md`。

## 文件清单

| 文件 | 用途 | 适用对象 | 必读 |
|------|------|---------|------|
| [使用手册.md](使用手册.md) | 启动指引 + 32 Skill 详解 + FAQ + 自检命令 | 所有用户 | ✅ |
| [部署说明.md](部署说明.md) | 跨平台部署（Windows / macOS / Linux）+ Java/JMeter/Allure 安装 + 升级 SOP | 运维 / 测试工程师 | ✅ |
| [配置清单.md](配置清单.md) | `.env` 全字段 + GitHub Secrets + Jenkins Credentials + Webhook 申请 | 所有用户 | ✅ |
| [交付物清单.md](交付物清单.md) | 测试计划 / 测试报告 / Bug 列表 等对外提交物落地位置 + 责任 + 格式 | 测试工程师 / 项目经理 | ⚪ 按需 |

## 推荐阅读顺序

| 角色 | 路径 |
|------|------|
| **新用户首次部署** | 部署说明 → 配置清单 → 使用手册 → 交付物清单 |
| **测试工程师日常** | 使用手册 → 交付物清单 |
| **运维 / DevOps** | 部署说明 → `ci/CICD集成说明.md` |
| **决策评审** | 根目录 `README.md` → `00-项目导航.md` → 本目录 |

## 快速链接

- 一键部署命令：见 [部署说明.md](部署说明.md) "GitHub 一键部署" 段
- 启动 Claude Code 后可调用的 32 Skill：见 [使用手册.md](使用手册.md) "技能（Skill）使用指南" 段
- `.env` 必填字段（最少 8 项）：见 [配置清单.md](配置清单.md) "2.1 必填字段"
- 提交物路径速查：见 [交付物清单.md](交付物清单.md) "1. 提交物速查表"

## 对应 Agent / Skill 调用示例

| 任务 | 在 Claude Code 提示符调用 |
|------|--------------------------|
| 5 分钟首测 | `> /smoke-test` |
| 完整流程 | `> /test-coordinator` |
| 用例设计 | `> /testcase-design` |
| 性能脚本 | `> /jmeter-script-gen` |
| 提 Bug | `> /zentao-bug-submission` |
