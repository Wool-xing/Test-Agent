---
id: pytest-fixture
category: 02-coding
level: 基础
name_zh: pytest fixture 注入
name_en: pytest fixtures
one_liner_zh: 测试前后置依赖注入;scope 决定共享粒度
one_liner_en: Dependency injection for setup/teardown; scope determines sharing
authority:
  - "Pytest Docs §How to use fixtures https://docs.pytest.org/en/stable/how-to/fixtures.html"
  - "Brian Okken 2022《Python Testing with pytest》ch.3-5"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何需要测试前/后置(数据库连接/临时文件/mock 服务/测试数据)
common_pitfall:
  - "scope 错(默认 function 重复建库)"
  - "yield 后清理代码异常不被报告"
  - "conftest.py 放错层级"
  - "fixture 间依赖循环"
example: |
  ```python
  @pytest.fixture(scope="session")
  def db():
      c = create_engine("sqlite:///test.db")
      yield c
      c.dispose()

  @pytest.fixture
  def user(db):
      uid = db.execute("INSERT ... RETURNING id").scalar()
      yield uid
      db.execute(f"DELETE FROM users WHERE id={uid}")
  ```
related_to: [pytest, mock-pattern, page-object]
---
