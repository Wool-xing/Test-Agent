---
name: tdd-workflow
description: TDD 测试驱动开发 Skill。Tests BEFORE code,80%+ 覆盖(unit+integration+E2E),边界+异常+错误场景必覆盖。派生自 ECC 同名 skill 。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# tdd-workflow

## 触发

- 新功能 / 修 bug / 重构 / 加 API endpoint / 新组件

## 核心原则

1. **Tests BEFORE Code**:**始终**先写测试,再实现让测试过
2. **80%+ 覆盖**:unit + integration + E2E
3. 边界 + 错误 + 异常 + 临界全覆盖

## 3 类测试矩阵

| 类型 | 范围 | 工具(本项目) |
|------|------|----------------|
| Unit | 函数 / 组件逻辑 / 纯函数 / helper | pytest + pytest-mock(`utils/`)|
| Integration | API endpoint / DB / 服务交互 / 外部 API | pytest + requests / playwright(API)|
| E2E | 关键用户流 / 浏览器自动化 / UI | Playwright(已配置) |

## TDD Workflow 步骤

1. **写 failing test**(red)
2. **写最少代码**让它过(green)
3. **重构**保持测试过(refactor)
4. 移到下一个测试 case

## 融合

- 测试深度横切准则:"用例本身用变异测试反向验证"(覆盖率 ≠ 用例质量)
- Karpathy 原则 4 Goal-Driven:每任务转为 "写复现测试 → 让它过"
- 修改四关:测试套件全过才许 commit

## 不做

- 不写无 assert 的测试
- 不一次写完 200 行测试不跑(分小批 red → green)
- 不为了覆盖率写无意义测试
