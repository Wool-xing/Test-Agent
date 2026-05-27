# orchestrator 索引

## 文件清单

| 文件 | 用途 |
|------|------|
| `flows.py` | Prefect `@flow` 主入口,接收 router DAG 跑全链路 |
| `tasks.py` | `@task` 原子(调专家/Skill/67 脚本) |
| `adapters/` | 包装 `utils/*.py` 67 脚本为 Prefect task |

## 编排能力

- 断点续跑(Prefect 自带状态机)
- 失败重试(每 task 默认 3 次,指数退避)
- 并发控制(`task_runner=ConcurrentTaskRunner`)
- 产物归档(每步 artifact 上传 MinIO,run_id 索引)
- 全链路 trace(OTel span 注入)

## 调度策略

1. router 出 DAG → flow 解析
2. 按依赖拓扑排序,无依赖并发
3. 每 task 完成写入飞轮(`storage.write_step`)
4. 失败:重试 / 跳过 / 终止(策略来自 DAG `on_failure` 字段)
