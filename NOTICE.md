# NOTICE · 上游致谢

Test-Agent 本体 MIT License。以下组件保留各自上游协议。

## Upstream Skills(项目内 skills/ 子目录)

| 路径 | 上游 | 协议 |
| ------ | ------ | ------ |
| `skills/darwin-skill/` | [alchaincyf/darwin-skill](https://github.com/alchaincyf/darwin-skill) | MIT |
| `skills/karpathy-guidelines/` | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | MIT |
| `skills/nuwa-skill/` | [alchaincyf/nuwa-skill](https://github.com/alchaincyf/nuwa-skill) | MIT |

各子目录含本地 `LICENSE` 副本(完整 MIT 全文 + 上游作者署名)。

## Python 依赖(主要)

详见 `config/requirements.txt`。常用:

- pytest(MIT)/ Playwright(Apache 2.0)/ Appium(Apache 2.0)/ pywinauto(BSD-3-Clause)
- JMeter(Apache 2.0)/ Allure(Apache 2.0)— 外部安装
- LiteLLM(MIT)
- Prefect 2.x/3.x(Apache 2.0)
- FastAPI(MIT)
- SQLAlchemy(MIT)
- pgvector(PostgreSQL License)
- MinIO Python SDK(Apache 2.0)
- OpenTelemetry(Apache 2.0)
- requests(Apache 2.0)
- anthropic / openai / google-generativeai 等 SDK(各自 MIT/Apache 2.0)
- bandit(Apache 2.0)/ pip-audit(Apache 2.0)/ safety(MIT)

## MCP 协议

[Model Context Protocol](https://modelcontextprotocol.io) — 开放标准,Anthropic 主导。Test-Agent MCP 实现该协议。

## 联络

协议争议、致谢遗漏、合规问题 → 见 [SECURITY.md](SECURITY.md) 联络方式。
