# storage 索引(飞轮)

## 文件清单

| 文件 | 用途 |
| ------ | ------ |
| `db.py` | SQLAlchemy 引擎/Session 工厂 |
| `models.py` | ORM:Run / Case / Defect / Evidence / Feedback / Embedding |
| `objects.py` | MinIO 客户端 |
| `migrations/` | Alembic 迁移 |

## 飞轮 schema

```text
runs       ── 一次执行(run_id/输入/状态/起止/产物索引)
cases      ── 测试用例(run_id/标题/优先级/步骤/结果)
defects    ── 缺陷(case_id/严重度/状态/根因/Bug 系统外链)
evidence   ── 证据(run_id 或 case_id/类型/MinIO key/hash)
feedback   ── 用户反馈(误报/漏报/标注/打标)
embeddings ── 向量(pgvector,case/defect 文本嵌入,用于历史检索)

```text

## 用途

- 历史检索:相似用例/相似缺陷
- AI 路由训练:用 feedback 修正后续路由
- 报告聚合:多次 run 趋势/回归基线
