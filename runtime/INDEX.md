# runtime 索引

> Test-Agent 运行时层。
> 顶层导航见根目录 `00-项目导航.md`；运行时完整章节见 `docs/charter/07-runtime-license.md`；架构设计见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

## 定位

把 16 专家定义 + 32 业务 Skill + 3 元 Skill + 79 脚本 从"文档+工具箱"升级为"可执行运行时"。
本层 **不动** `agents/` `skills/` `utils/` 已有内容,仅作调度。

## 模块清单

| 模块 | 路径 | 用途 |
| ------ | ------ | ------ |
| AI 路由 | [router/](router/INDEX.md) | 被测物 → 专家+Skill 组合 → DAG |
| 注册中心 | [registry/](registry/INDEX.md) | 扫描 16 专家 + 32 业务 Skill + 3 元 Skill frontmatter,统一目录 |
| Prefect 编排 | [orchestrator/](orchestrator/INDEX.md) | 执行 DAG,断点续跑,产物归档 |
| FastAPI 入口 | [api/](api/INDEX.md) | `/run` `/status` `/report` `/catalog` |
| Typer CLI | [cli/](cli/INDEX.md) | `tagent run/plan/catalog/doctor` |
| 飞轮存储 | [storage/](storage/INDEX.md) | Postgres+pgvector + MinIO |
| 观测 | [observability/](observability/INDEX.md) | OpenTelemetry + Loguru |
| 配置 | `config/` | pydantic-settings |
| 测试 | `tests/` | 运行时自身的单测 |

## 启动顺序

```
1. docker compose up -d            # 依赖(postgres/minio/prefect)
2. alembic upgrade head            # 飞轮 schema
3. tagent catalog                  # 校验注册中心
4. tagent run <被测物>             # CLI 单次跑
   或 uvicorn runtime.api.main:app # HTTP 服务
```

## 与已有层关系

```
用户输入(任意格式)
   │
   ▼
runtime/api 或 runtime/cli      ← 新增,统一入口
   │
   ▼
runtime/router                  ← 新增,AI 决策
   │ (DAG: 专家组合 + Skill 调用顺序)
   ▼
runtime/orchestrator            ← 新增,Prefect 编排
   │
   ├─► agents/*.md         ← 已有,文档→Claude Code 加载
   ├─► skills/*.md         ← 已有,文档→Skill 调用
   └─► utils/*.py         ← 已有,79 脚本(adapter 包装)
   │
   ▼
runtime/storage 飞轮            ← 新增,数据沉淀
   │
   ▼
报告 + 通知                      ← 复用已有 utils/
```

## 对应任务

- M1-1 骨架(本文件) | M1-2 router | M1-3 registry | M1-4 orchestrator
- M1-5 api | M1-6 cli | M1-7 storage | M1-8 observability
- M1-9 docker-compose | M1-10 E2E demo | M1-11 文档同步+版本 bump
