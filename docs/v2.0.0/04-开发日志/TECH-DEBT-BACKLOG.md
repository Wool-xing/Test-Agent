# 技术债务 Backlog — 延期项追踪

> 协议: §零.2 Step D — 无法修复或主动延期的项目
> 规则: 每Sprint结束复查此清单, 已到解决时间的必须处理

---

## 从各报告行动清单中提取的延期项

| ID | 来源 | 严重级 | 问题 | 延期原因 | 计划Sprint | 状态 |
|----|------|--------|------|---------|-----------|------|
| TD-001 | -1.3 断链清单 D-003 | LOW | 42个图谱孤立节点调查 | 多为文档/stub节点, 非真死代码 | Sprint 6 (知识图谱集成时) | ⏸️ |
| TD-002 | -1.5 复发清单 R-A1 | HIGH | install.py 回归测试 | 安装脚本在Sprint 7发布准备时验证 | Sprint 7 | ⏸️ |
| TD-003 | -1.5 复发清单 R-A2 | HIGH | skins.py 回归测试 | 皮肤系统稳定后再加测试 | Sprint 2A | ⏸️ |
| TD-004 | §七 质量门禁 G-001 | HIGH | 覆盖率 34%→80% | 需~3600测试, 随Sprint推进累计 | 持续 (每Sprint+5%) | 🔧 |
| TD-005 | 补-12 性能 | MEDIUM | 6/14性能项未测量 | 需后续Sprint环境(并发/Docker/移动端) | Sprint 5-10 | ⏸️ |
| TD-006 | 补-6 | MEDIUM | WCAG 2.2 验证 | 需Web Dashboard就绪(Sprint 4) | Sprint 4 | ⏸️ |
| TD-007 | 补-7 | HIGH | 自测闭环CI集成 | 需Test-Agent自身可发布(Sprint 7) | Sprint 7 | ⏸️ |
| TD-008 | 补-14 | MEDIUM | 持续证据收集 | 需/loop持续运行积累 | 每次/loop | 🔧 |
| TD-009 | 补-27 | MEDIUM | README截图/GIF | 需TUI真机GUI环境 | Sprint 4 (Web) + Sprint 7 (CLI) | ⏸️ |
| TD-010 | §三-C DR-005 | MEDIUM | interactive.py multiline死代码(70行) | 低风险, 仅被测试引用 | Sprint 3 | ⏸️ |
| TD-011 | §三-C DR-006 | MEDIUM | interactive.py 全局状态耦合 | 需架构调整, 不应在补丁中做 | Sprint 6 | ⏸️ |
| TD-012 | §三-C DR-008 | MEDIUM | task状态无转换守卫 | 需设计状态机, 工作量较大 | Sprint 5 | ⏸️ |
| TD-013 | §三-C | LOW | 逐文件深审 (362/364 剩余) | 全量364文件不可行, 高风险文件优先 | 持续 (每Sprint审10文件) | 🔧 |
| TD-014 | 补-36 | MEDIUM | 文档一致性自动检查CI集成 | 脚本已写, 未集成CI/pre-commit | Sprint 3 | ⏸️ |

---

## 统计

| 严重级 | 数量 | 说明 |
|--------|------|------|
| HIGH | 3 | 覆盖率/install测试/自测CI |
| MEDIUM | 9 | 性能/WCAG/证据/截图/死代码/耦合/状态机/文档检查 |
| LOW | 2 | 图谱节点/逐文件深审 |
| 🔧 进行中 | 3 | 覆盖率(持续)/证据(每次/loop)/深审(每Sprint) |
| ⏸️ 延期 | 11 | 有明确计划Sprint, 不丢失 |

## 复查协议

每个Sprint结束时:
1. 检查本Sprint到期的TD项 → 必须处理
2. 标注进展(覆盖率+?%, 深审+?文件)
3. 新增延期项 → 追加到此清单
4. 已完成项 → 标注✅ + 移到"已关闭"章节

---
*创建: 2026-06-21 | 下次复查: Sprint 3结束*
