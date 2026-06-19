---
id: shift-left
category: 04-strategy
level: 基础
name_zh: Shift-Left 左移测试
name_en: Shift-Left Testing
one_liner_zh: 测试介入越早越便宜(Boehm 指数代价法则)
one_liner_en: The earlier you test, the cheaper to fix (Boehm exponential cost law)
authority:

  - "Boehm 1981《Software Engineering Economics》— 缺陷修复成本 1× → 200× 指数律"
  - "Martin Fowler《CI Pipeline》"
  - ISTQB Foundation §1.4 测试七原则(早测试)
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何项目;
common_pitfall:

  - "只测开发末端 → 修复成本爆炸"
  - "需求阶段不评审 → 测试用例无所依"
  - "Pre-commit hook 缺失 → 垃圾进库"
example: |
  7 层介入点:

  - L1 需求 → 测试架构评审
  - L2 设计 → 等价类/边界值/状态迁移
  - L3 IDE → ruff + mypy 实时
  - L4 pre-commit → gitleaks + 私源防护
  - L5 PR gate → CodeQL + pip-audit + safety
  - L6 静态分析 → Bandit + ZAP/Burp
  - L7 契约 → Pact / openapi 测试
related_to: [shift-right, test-pyramid-2024, mutation-testing]
reading_zh:

  - "美团技术博客《研发左移实践》"
reading_en:

  - https://martinfowler.com/articles/continuousIntegration.html
---
