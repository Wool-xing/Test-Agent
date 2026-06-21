# 阶段-1.3 可执行行动清单

> 来源: 断链清单.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环

## 行动项

| 编号 | 严重级 | 问题描述 | 修复方案 | 验证方式 | 状态 |
|------|--------|---------|---------|---------|------|
| D-001 | HIGH | skills.registry 导入失败 | 添加 registry = SKILL_RUNNERS | `from runtime.orchestrator.skills import registry` 成功 | ✅ |
| D-002 | LOW | 15个文件有未使用导入 | 逐文件删除未使用import | grep确认0残留 | ✅ |
| D-003 | LOW | 42个图谱孤立节点 | Sprint 0逐节点确认 | 死代码率≤5% | ⏸️ 延期(低优先级) |
| D-004 | LOW | import-linter精确检测 | CI集成import-linter | 0循环依赖 | ⏸️ TD-018, Sprint 4 CI完善 |

## 验证记录

- D-001: `python -c "from runtime.orchestrator.skills import registry"` → dict type, PASS
- D-002: 9个文件已确认删除未使用导入, 6个经验证实际使用中
- D-003: 42节点大部分为文档/stub, 非死代码, 延期处理
