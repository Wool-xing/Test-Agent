# scripts/ 索引(V1.10.0)

> 运维 / 分析 / 数据导出脚本 · 不属于运行时 · 不进入 tagent CLI。

## 速查表

| 文件 | 用途 | 跑法 |
|------|------|------|
| `analyze-usage.py` | skill / agent 使用率分析(cut/keep 矩阵:keep_core ≥10% / keep_mid 3-10% / deprecate <3% / archive 0%) | `python scripts/analyze-usage.py --input usage.json` |
| `export-users.sql` | 用户画像 + top skill + 0% skill + 留存 + 反馈 5 段 SQL 模板(含 PII 脱敏正则) | 接入 Postgres 后 `psql -f scripts/export-users.sql` |

## 新手 5 分钟

- 没运维 / 数据需求,**这个目录可以略过**
- 想看用户怎么用 skill → 跑 `analyze-usage.py` 看分布
- 想做用户画像 → `export-users.sql` 改 WHERE 条件即用

## 高级用法

- 加新脚本前问:**这个能进 runtime CLI 子命令吗?** 能 → 放 `runtime/cli/`;不能(一次性 / SQL / 运维)→ 放本目录
- 脚本必带 `--dry-run` 选项(防生产误操作)
- 涉及真实数据的脚本输出**禁止入 repo**(用 `workspace/` 临时存放,加 `.gitignore`)

## 相关

- 上一级:[`../README.md`](../README.md)
- 主宪章 §0(安全:真实数据隔离)+ §19-12(决策可追溯)
