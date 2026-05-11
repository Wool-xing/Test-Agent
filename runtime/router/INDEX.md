# router 索引

## 文件清单

| 文件 | 用途 |
|------|------|
| `llm_client.py` | LiteLLM 多厂商封装 + Ollama 兜底 |
| `expert_loader.py` | 扫描 `02-专家定义/*.md` frontmatter |
| `skill_loader.py` | 扫描 `03-技能定义/*.md` frontmatter |
| `prompt.py` | 路由 system prompt(指导 LLM 选专家+Skill) |
| `schema.py` | DAG/Decision Pydantic 模型 |
| `router.py` | 主路由:被测物 → Decision(experts/skills/order/confidence/rationale) |

## 准确率门槛

- M1 收口 ≥85%(3 类典型输入:Web 系统/REST API/移动 App,每类 10 样本)
- 不达 → 双模型投票(Claude+Qwen),仍不达 → 兜底全调

## 多厂商支持

`LLM_PROVIDER` 环境变量,可填:
`claude` `openai` `gemini` `qwen` `deepseek` `ollama`(本地)

`LLM_PROVIDER_FALLBACK` 失败回退,默认 `ollama`。
