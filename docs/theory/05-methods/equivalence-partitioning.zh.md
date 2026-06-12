---
id: equivalence-partitioning
category: 05-methods
level: 基础
name_zh: 等价类划分
name_en: Equivalence Partitioning
one_liner_zh: 输入域按"等价行为"切类,每类取一代表测
one_liner_en: Partition input domain into equivalence classes; one representative per class
authority:
  - "ISTQB Foundation v4.0 §4.3.1 Equivalence Partitioning"
  - "Beizer 1990《Software Testing Techniques》(2nd ed) ch.3"
  - "Myers 2011《The Art of Software Testing》(3rd ed) ch.4"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 输入域可分类、类内表现一致(数值范围/选项枚举/字符串长度)
common_pitfall:
  - "漏负边界(年龄字段忘了 <0)"
  - "漏空值/null/缺失"
  - "数值类型边界(int32 overflow)"
  - "和边界值不同时用 → 漏临界缺陷"
example: |
  字段:年龄 1-120 整数
  等价类:
  - 有效:1-120
  - 无效-低:<1(0/-1)
  - 无效-高:>120(121)
  - 无效-类型:非数字 "abc" / 空字符串 / null
  - 无效-边界:小数 1.5
related_to: [boundary-value-analysis, decision-table, pairwise-testing]
reading_zh:
  - 阿里测试学院《等价类划分实战》
reading_en:
  - "ISTQB Foundation Syllabus v4.0 §4.3.1"
  - "Glenford Myers The Art of Software Testing ch.4"
---

# 等价类划分

把"输入域"切成若干"等价类",同一类内表现一致,**每类取一代表**测即可——这是 ISTQB Foundation §4.3.1 的核心黑盒技术。

## 步骤
1. 列输入条件(字段/参数/选项)
2. 按"行为是否一致"切类
3. 每类标 有效(valid) / 无效(invalid)
4. 每类至少一用例覆盖
5. 配合**边界值分析**测临界点

## Test-Agent 用法
- `testcase-designer` 专家(agents/03-用例设计.md)默认套此法
- Excel 输出 4 Sheet 含等价类表

## 为什么这么做?
- 大幅减少用例数(不必每个值都测)
- 失败定位快(同类内一例失败,整类有问题)
- 与边界值配合,90% 输入缺陷可覆盖

## 反模式
- 漏无效类(只测好路径)= **测试不诚信**
- 类切太细 = 用例数爆炸,失去抽象价值
