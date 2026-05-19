---
id: pytest
category: 01-tools
level: 基础
name_zh: pytest
name_en: pytest
one_liner_zh: Python 测试事实标准,fixture+插件生态最强
one_liner_en: De facto Python testing framework with the richest fixture+plugin ecosystem
authority:
  - "Pytest Official Docs v8.x https://docs.pytest.org"
  - "Brian Okken《Python Testing with pytest》(2nd ed, 2022)"
  - ISTQB Foundation §6.2.2 测试自动化工具
confidence: high
last_reviewed: 2026-05-11
reviewer: agent-curator
when_to_use: Python 项目任何层级测试(单元/集成/E2E);需要 fixture 注入/参数化/插件扩展
common_pitfall:
  - "fixture scope 默认 function;数据库连接没设 module/session 导致重复创建"
  - "未用 pytest-xdist 并行 → 大型套件几小时跑不完"
  - "conftest.py 放错层级 → fixture 跨包不可见"
example: |
  ```python
  import pytest

  @pytest.fixture(scope="session")
  def db():
      conn = create_connection()
      yield conn
      conn.close()

  @pytest.mark.parametrize("input,expected", [(1, 2), (3, 4)])
  def test_add_one(input, expected):
      assert add(input, 1) == expected
  ```
related_to: [pytest-fixture, pytest-xdist, allure-pytest, mock]
reading_zh:
  - https://docs.pytest.org/zh-cn/latest/
  - 美团技术博客《pytest 在美团的实践》
reading_en:
  - https://docs.pytest.org/en/stable/
  - "Brian Okken 2022 ch.3 Fixtures"
---

# pytest

Python 测试事实标准。本项目 `runtime/` 全栈 pytest;`config/pytest.ini` 已配齐。

## 在本项目调用
- 任何 `runtime/tests/test_*.py` 文件 → `pytest runtime/tests/`
- E2E smoke:`runtime/tests/test_smoke_e2e.py`
- Router 准确率:`runtime/tests/test_router_real.py`

## 核心概念
- **fixture**:测试前后置;`@pytest.fixture(scope="session"|"module"|"class"|"function")`
- **参数化**:`@pytest.mark.parametrize` 一组用例多组数据
- **marker**:`@pytest.mark.smoke / regression / slow` 分类筛选
- **conftest.py**:自动加载的 fixture 文件
- **plugin 生态**:`pytest-xdist`(并行)/`pytest-cov`(覆盖率)/`pytest-bdd`(BDD)/`allure-pytest`(报告)

## 为什么 Agent 调用 pytest?
被测物是 Python 项目 → 单元+集成层首选 pytest;输出 junit-xml 喂 Allure;并行用 xdist;失败重试用 rerunfailures。
