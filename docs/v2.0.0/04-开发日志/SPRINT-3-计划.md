# Sprint 3 计划 — 扩展体系

> 日期: 2026-06-21
> 协议: §五-A Sprint 3
> 状态: 🔧 执行中

---

## 已完成 (前序Sprint遗留)

| 功能 | 状态 | 证据 |
|------|------|------|
| Skill SDK scaffold | ✅ | PR #412, 4/4 TDD |
| Skill SDK validate | ✅ | PR #412, 4/4 TDD |
| Skill SDK package | ✅ | PR #412, 2/4 TDD |
| Skill SDK publish | ✅ | PR #412, 2/4 TDD |
| SDK discovery | ✅ | 5/5 TDD (本会话) |
| build_catalog extra_skill_dirs | ✅ | registry集成 |
| skill list 命令 | ✅ | 37 skills listed |
| skill search 命令 | ✅ | keyword过滤 |

## 待完成

| # | 功能 | TDD | 预计 |
|---|------|-----|------|
| 3.1 | skill install 命令 | ⬜ | 安装本地Skill目录到workspace |
| 3.2 | skill test 命令 | ⬜ | 运行Skill自带测试 |
| 3.3 | MCP list/info 命令 | ⬜ | 发现外部MCP Server工具 |
| 3.4 | 3个示例Skill | ⬜ | demo-http / demo-file / demo-notify |
| 3.5 | Skill开发文档 | ⬜ | docs/v2.0.0/05-开发指南/Skill开发.md |
| 3.6 | Skill市场本地registry | ⬜ | tagent skill publish到本地市场 |

## 验收标准 (§五-A)

- 🤖 tagent skill install ./my-skill → 安装成功
- 🤖 tagent skill test my-skill → 通过
- 🤖 tagent mcp list → 发现MCP工具
- 🤖 tagent skill search "http" → 返回结果
- 👤 开发者30分钟完成「创建→本地测试→发布」

## 日任务拆分

| 日 | 任务 |
|----|------|
| Day 1 | skill install + test TDD → GREEN |
| Day 2 | MCP list/info + 3示例Skill |
| Day 3 | Skill开发文档 + 本地市场 |
| Day 4 | 代码审查 + 安全检查 + /loop |
| Day 5 | 验收 + 四维自评 + 门禁检查 |
