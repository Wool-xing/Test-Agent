# subagent 索引

> 派生自 `D:/项目文件/_精髓库/hermes-agent.md §1.3`。

## 规则(主宪章 §22)

- **隔离 client**:子代理用 `auxiliary` LLM client,永不污染主 session prompt cache
- **ThreadPool 动态调整**:默认 32 workers,可按并发 evals 数 resize_tool_pool
- **失败隔离**:子 agent crash 不影响父 session
- **结果归并(非过程)**:只回传最终结果,不回灌中间 reasoning

## 文件清单

| 文件 | 用途 |
|------|------|
| `pool.py` | 全局 ThreadPoolExecutor + `resize_pool()` |
| `spawn.py` | `spawn_subagent(prompt, *, model_override=None) -> Future` |
| `aux_client.py` | 辅助 LLM client(不共享主缓存) |
