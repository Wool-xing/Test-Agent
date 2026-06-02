# learning_loop 索引

> 主宪章 §14 darwin-skill 是 skill 文本本身的棘轮;本模块是**外层协调器**:
> session 检索 + 用户画像 + curator 触发 + skill 自创建提示。

## 不变量(与 hermes 同源)

- **只动 agent-created skill**(不动 agents/skills已有)
- **绝不自动删,只归档**(`workspace/learning/archive/`)
- **Pinned skill 绕过所有自动**
- **用 auxiliary client**(`runtime/subagent/aux_client`)
- **不污染主 session prompt cache**

## 文件清单

| 文件 | 用途 |
|------|------|
| `curator.py` | 闲置触发的后台 skill 维护协调器 |
| `session_search.py` | FTS5 跨会话检索(SQLite + LLM 摘要) |
| `user_model.py` | 跨会话用户画像(类 Honcho dialectic) |
| `skill_lifecycle.py` | agent-created skill 生命周期(created→active→stale→archived) |

## 与 darwin-skill 协作

```
learning_loop/curator   (协调:何时跑+谁来跑)
        ↓ 触发
darwin-skill/SKILL.md   (执行:8 维评分+棘轮)
        ↓ 落
workspace/测试报告/{项目名}/skill-evolution/results.tsv
```
