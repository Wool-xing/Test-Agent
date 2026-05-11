# NOTICE · 上游致谢

Test-Agent 本体 MIT License。以下组件保留各自上游协议。

## Upstream Skills(项目内 03-技能定义/ 子目录)

| 路径 | 上游 | 协议 | 说明 |
|------|------|------|------|
| `03-技能定义/darwin-skill/` | [alchaincyf/darwin-skill](https://github.com/alchaincyf/darwin-skill) | MIT | upstream 原文不改本地 fork(主宪章 §14) |
| `03-技能定义/karpathy-guidelines/` | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | MIT | upstream 原文不改本地 fork(主宪章 §27) |

## 精髓萃取(`D:/项目文件/_精髓库/`,跨项目复用)

仅萃取**思想 / 模式 / 工程哲学**,不复制源码。每文档含致谢。

| 精髓文件 | 源项目 | 源 License |
|----------|--------|-----------|
| `hermes-agent.md` | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | MIT |
| `gbrain.md` | [garrytan/gbrain](https://github.com/garrytan/gbrain) | (查源) |
| `karpathy-skills.md` | [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) | MIT |
| `everything-claude-code.md` | [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | MIT |
| `pentest-ai-agents.md` | [vxcontrol/pentagi](https://github.com/vxcontrol/pentagi) + [KeygraphHQ/shannon](https://github.com/KeygraphHQ/shannon) | 各自 License;**shannon Lite 是 AGPL-3.0**,本项目仅萃取思想不复制代码 |
| `build-your-own-x.md` | [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) | CC0-1.0(公共领域)|

## Python 依赖(主要)

详见 `04-配置文件/requirements.txt`。常用:

- pytest / Playwright / Appium / pywinauto(各自 License)
- JMeter / Allure(各自 License,外部安装)
- LiteLLM(MIT)
- Prefect 2.x/3.x(Apache 2.0)
- FastAPI(MIT)
- SQLAlchemy(MIT)
- pgvector(PostgreSQL License)
- MinIO Python SDK(Apache 2.0)
- OpenTelemetry(Apache 2.0)

## MCP 协议

[Model Context Protocol](https://modelcontextprotocol.io) — 开放标准,Anthropic 主导。Test-Agent MCP 6 件套实现该协议。

## 复用模式

Test-Agent 复用上述项目的**架构模式 / 工程哲学**,**不复制源码**。所有复用均标注源 + 致谢。如有协议冲突或致谢遗漏,请提 issue,我们立刻修正。
