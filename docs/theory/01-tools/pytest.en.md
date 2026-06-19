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
  - ISTQB Foundation §6.2.2 Test Automation Tools
confidence: high
last_reviewed: 2026-05-11
reviewer: agent-curator
when_to_use: Any Python testing layer (unit/integration/E2E); needs fixture injection / parametrization / plugin extension
common_pitfall:

  - "Default fixture scope is `function` — DB connections recreated every test if scope not set to module/session"
  - "No pytest-xdist parallel → large suites take hours"
  - "Misplaced `conftest.py` → fixtures invisible across packages"
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
reading_en:

  - https://docs.pytest.org/en/stable/
  - "Brian Okken 2022 ch.3 Fixtures"
---

# pytest

De facto Python testing standard. This project's `runtime/` uses pytest end-to-end; `config/pytest.ini` is preconfigured.

## Invocation in this project

- Any `runtime/tests/test_*.py` → `pytest runtime/tests/`
- E2E smoke: `runtime/tests/test_smoke_e2e.py`
- Router accuracy: `runtime/tests/test_router_real.py`

## Core concepts

-**fixture**: setup/teardown; `@pytest.fixture(scope="session"|"module"|"class"|"function")`
-**parametrize**: one test, many inputs
-**marker**: classify with `@pytest.mark.smoke / regression / slow`
-**conftest.py**: auto-loaded fixture file
-**plugin ecosystem**: `pytest-xdist` (parallel) / `pytest-cov` (coverage) / `pytest-bdd` (BDD) / `allure-pytest` (reports)

## Why does the Agent call pytest

Subject is a Python project → pytest is the first choice for unit+integration; outputs junit-xml feeding Allure; parallelize via xdist; retry flakes via rerunfailures.
