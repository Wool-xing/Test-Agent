---
id: test-pyramid-2024
category: 03-foundation
level: 基础
name_zh: 测试金字塔 2024 现代版
name_en: Test Pyramid 2024
one_liner_zh: 单元 40 / 集成 30 / 契约 20 / E2E 10 + 变异反验
one_liner_en: Unit 40 / Integration 30 / Contract 20 / E2E 10 + mutation reverse-check
authority:
  - "Mike Cohn 2009《Succeeding with Agile》ch.16(原版金字塔)"
  - "Martin Fowler https://martinfowler.com/articles/practical-test-pyramid.html"
  - "Google Testing Blog 2024 doc on pyramid"
  - ISO/IEC 25010 §4 Quality Model
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何项目测试架构设计前;主宪章 §17 落点
common_pitfall:
  - "70/20/10 一刀切——按变更频率+阻塞代价重新分布才合理"
  - "把视觉回归当成独立层——它属 E2E"
  - "无变异测试 → 覆盖率不等于用例质量"
example: |
  ```
          E2E + 视觉回归  10%   ← Playwright / Appium / Airtest
          契约 + 系统     20%   ← Pact / openapi / WireMock
          集成 + 组件     30%   ← pytest + pytest-mock
          单元           40%   ← pytest(秒级) + 变异测试反验
  ```
related_to: [shift-left, shift-right, mutation-testing, contract-testing]
reading_zh:
  - 阿里测试学院《微服务时代的测试金字塔》
reading_en:
  - https://martinfowler.com/articles/practical-test-pyramid.html
  - "Google Testing Blog: Just say no to More End-to-End Tests"
---

# 测试金字塔 2024 现代版

经典金字塔(Mike Cohn 2009):单元 70 / 集成 20 / E2E 10。

**2024 调整**(Google/Microsoft/Fowler 综合):按"变更频率+阻塞代价"分配,**不再一刀切**:

- 单元 40 / 集成 30 / 契约+系统 20 / E2E+视觉回归 10
- 单元层叠加**变异测试**反向验证用例有效性
- 契约层独立成层(微服务时代必备)
- 视觉回归归 E2E,不另设层

## Test-Agent 落点

- 单元:`pytest + pytest-mock`(utils 自测,Phase 2 补齐)
- 集成:pytest 内嵌 + WireMock
- 契约:`utils/contract_test.py`(Pact + jsonschema)+ `utils/openapi_test_gen.py`
- E2E:Playwright(Web/Electron)+ Appium(移动)+ Airtest(视觉)
- 变异:`utils/mutation_runner.py`(mutmut)

## 为什么 Agent 这么分配?

- 单元最便宜最快 → 多写
- E2E 最贵最脆 → 少写
- 契约层填补微服务断点 → 必有
- 变异分数 ≠ 覆盖率(主宪章 §21 横切准则)→ 用例质量反验
