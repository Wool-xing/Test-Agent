# registry 索引

## 文件清单

| 文件 | 用途 |
|------|------|
| `registry.py` | 扫 agents/*.md + skills/*.md frontmatter,生成内存目录 |
| `catalog.json` | 启动时生成,可手动 dump 给 LLM 用 |

## frontmatter 约定(已有)

```yaml
---
name: <id>
description: <一句话职责>
tools: <逗号分隔工具列表,可选>
---
```

## 用途

- `router` 读 catalog 喂 LLM 选专家+Skill
- `orchestrator` 按 catalog 决定调度顺序
- `api/catalog` 暴露给前端/CLI 用户查看
