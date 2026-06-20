# SBOM 生成报告 — Sprint 0-2A

> 提示词: 补-11 依赖安全审计 | 格式: CycloneDX
> 日期: 2026-06-21

---

## Python依赖清单 (主要)

| 包 | 版本 | 用途 | 许可证 |
|---|------|------|--------|
| typer | >=0.15 | CLI框架 | MIT |
| rich | >=13.0 | 终端美化 | MIT |
| textual | >=1.0 | TUI框架 | MIT |
| prompt_toolkit | >=3.0 | REPL交互 | BSD |
| pydantic | >=2.13.4 | 数据验证 | MIT |
| pydantic-settings | >=2.0 | 配置管理 | MIT |
| loguru | >=0.7 | 日志 | MIT |
| litellm | >=1.0 | LLM多Provider | MIT |
| httpx | >=0.27 | HTTP客户端 | BSD |
| fastapi | >=0.115 | API服务 | MIT |
| uvicorn | >=0.34 | ASGI服务 | BSD |
| pyyaml | >=6.0 | YAML解析 | MIT |
| pytest | >=8.0 | 测试框架 | MIT |
| pytest-cov | >=6.0 | 覆盖率 | MIT |

## 依赖安全状态

| 检查 | 状态 |
|------|------|
| pip-audit CVE扫描 | ✅ CI自动执行, 0 CRITICAL |
| Dependabot | ✅ 已启用, 自动提PR |
| 锁文件提交 | ✅ poetry.lock / package-lock.json |

## 缺失项

| 项目 | 状态 |
|------|------|
| CycloneDX SBOM JSON | ❌ 未自动生成 |
| SPDX SBOM | ❌ 未生成 |
| 依赖混淆防护 | ❌ 未实现 (补-11附件) |

---

*报告生成: 2026-06-21 | Sprint 7发布前需生成完整SBOM*
