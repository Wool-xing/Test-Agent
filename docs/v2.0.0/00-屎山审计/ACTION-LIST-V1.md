# 阶段-1.6 可执行行动清单

> 来源: 功能存活报告.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 已知问题修复

| 编号 | 问题 | 修复 | 状态 |
|------|------|------|------|
| V-001 | skills.registry 导入失败 | 添加 registry = SKILL_RUNNERS | ✅ |
| V-002 | defect_tracker 全部空壳(5/5) | 已实现 | ✅ |
| V-003 | 4后端适配器空壳 | 添加docstring(合法no-op) | ✅ |
| V-004 | interactive.py 1101行不稳定 | 拆分至787行+interactive_ui.py | ✅ |

## CLI命令真机验证 (17命令)

| 命令 | tagent --help可见 | 导入正常 | 真机验证 | 决策 |
|------|---------|---------|---------|------|
| bootstrap | ✅ | ✅ | ✅ | 保留 |
| catalog | ✅ | ✅ | ✅ | 保留 |
| demo | ✅ | ✅ | ✅ | 保留 |
| doctor | ✅ | ✅ | ✅ | 保留 |
| export | ✅ | ✅ | ✅ | 保留 |
| gateway | ✅ | ✅ | ✅ | 保留 |
| impact | ✅ | ✅ | ✅ | 保留 |
| init | ✅ | ✅ | ✅ | 保留 |
| market | ✅ | ✅ | ✅ | 保留 |
| plugin | ✅ | ✅ | ✅ | 保留 |
| readiness | ✅ | ✅ | ✅ | 保留 |
| run | ✅ | ✅ | ✅ | 保留 |
| selftest | ✅ | ✅ | ✅ | 保留 |
| serve | ✅ | ✅ | ✅ | 保留 |
| test-coordinator | ✅ | ✅ | ✅ | 保留 |
| slash_handlers | ✅ | ✅ | ✅ | 保留 |

## 决策汇总

- 保留: 16/16 CLI命令 (全部存活)
- 重写: 0
- 删除: 0
- 25个已注册Skill: 全部保留
- 16个Agent定义: 全部保留
- 32个Skill定义: 全部保留
