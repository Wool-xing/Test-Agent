# Sprint 0 可执行行动清单

> 来源: SPRINT-0-验收报告.md
> 提取日期: 2026-06-21
> 协议: §零.2 报告→行动强制闭环 Step B

## 交付物缺口

| 编号 | 严重级 | 验收项 | 报告状态 | 实际状态 | 修复 | 状态 |
|------|--------|--------|---------|---------|------|------|
| S0-001 | HIGH | 所有文件 ≤ 800行 | ⚠️ interactive.py 1101行(延期) | ✅ 已拆分至787行+interactive_ui.py 399行 | 已完成 | ✅ |
| S0-002 | MEDIUM | 3平台构建全部通过 | ⚠️ Windows已验证, macOS/Linux待确认 | ✅ CI三平台绿色 | 已完成 | ✅ |
| S0-003 | MEDIUM | 所有函数 ≤ 50行 | ✅ (最大54行, run_decision_direct) | ✅ 所有≤50行 | 已完成 | ✅ |
| S0-004 | MEDIUM | make setup 执行成功 | pip install -e ".[dev]" + devcontainer.json | ✅ 已可用 | ✅ |
| S0-005 | MEDIUM | 四维达成度自评 | 易维护35%/易扩展20%/易体验15%/易开发45% | 已更新: 55/45/60/50% | ✅ |
| S0-006 | LOW | 硬编码47个(文档/配置) | 已复查: Discord URL已提取, 其余为文档示例 | 扫描0发现 | ✅ |

## 行动项执行

| 编号 | 行动 | 状态 |
|------|------|------|
| S0-A1 | 更新四维达成度 | ✅ 四维达成度自评-Sprint0-2A.md |
| S0-A2 | 验证 make setup 执行 | ✅ pip install -e ".[dev]" + devcontainer |
| S0-A3 | 复查硬编码47个 | ✅ 扫描0发现 (evidence/sprint-0-verification.txt) |

## 二次验证

- [ ] 重新运行 claude-crap:score 确认 CRAP≥C
- [ ] 全量测试通过
