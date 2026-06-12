---
id: bug-lifecycle
category: 12-process
level: 基础
name_zh: 缺陷生命周期
name_en: Defect Lifecycle
one_liner_zh: New→Open→InProgress→Resolved→Verify→Closed,严重度优先级分离
one_liner_en: New→Open→InProgress→Resolved→Verify→Closed; severity vs priority decoupled
authority:
  - ISTQB Foundation §5.5 缺陷管理
  - IEEE 1044《Standard Classification for Software Anomalies》
  - "OWASP CWE Severity Rating"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何 Bug Tracker(zentao/jira/github/linear/...)接入
common_pitfall:
  - "严重度+优先级混为一谈(技术 vs 业务两个维度)"
  - "无 reopen 处理 → flaky bug 反复被关"
  - "无 root cause 字段 → 缺陷分析无据"
  - "未链测试用例 → 无法回归验证"
example: |
  状态机:
  New → Open → InProgress → Resolved → Verify → Closed
                                  └→ Rejected
                                  └→ Deferred
  reopen: Closed → Open(失败回归触发)

  严重度(技术影响):1=P0 / 2=P1 / 3=P2 / 4=P3
  优先级(业务紧急):同样四级,但**与严重度独立**
related_to: [rca-5why-8d-fishbone, bug-tracker-adapters]
---

# 缺陷生命周期

Test-Agent **统一权威**:`utils/bug_severity_map.py` 跨 5 adapter(zentao/jira/github/linear/webhook)一致 1=P0/2=P1/3=P2/4=P3。

## 严重度 vs 优先级(必懂)
- **严重度**:bug 技术影响(崩溃 vs 显示错位)
- **优先级**:修复紧急度(老板用 vs 客户偶遇)
- **两者独立**:可能"P3 优先级 + P0 严重度"(数据丢失但只影响 1% 用户)

## RCA 标准方法
- 5Why:连问 5 个为什么
- 8D:8 步纪律(团队+护栏+遏制+根因+永久解+预防)
- Fishbone:鱼骨图分类(人/机/料/法/环/测)
