# config 索引

> 顶层导航见根目录 `00-项目导航.md`；配置项详解见 `docs/getting-started/配置清单.md`。

## 文件清单

| 文件 | 用途 | 是否提交 Git |
|------|------|------------|
| [conftest.py](conftest.py) | pytest 全局 fixture（项目根唯一权威：`EnvConfig` / `env_config` / `test_data` / `browser_context` / `api_client` / 失败截图 hook） | ✅ |
| [pytest.ini](pytest.ini) | pytest 行为：markers / addopts / timeout / junit-xml / log | ✅ |
| [requirements.txt](requirements.txt) | Python 依赖（`==` 锁版本，CI 可复现） | ✅ |
| [.env.example](.env.example) | 环境变量模板（占位值，复制为 `.env` 后填实值） | ✅ 模板提交，`.env` 不提交 |
| [.mcp.json](.mcp.json) | MCP 服务配置（当前仅启用 filesystem；其他通道 SDK 直连） | ✅ |
| [mcp-server-impl.md](mcp-server-impl.md) | MCP server 自实现教程（zentao / wechat / feishu / dingtalk 骨架，按需启用） | ✅ |

## 配置生效位置

| 配置文件 | 部署后落地位置 | 是否覆盖用户修改 |
|---------|---------------|----------------|
| `conftest.py` | `<PROJECT_ROOT>/conftest.py` | 升级时**覆盖**（用户自定义请抽到 `tests/conftest_user.py`） |
| `pytest.ini` | `<PROJECT_ROOT>/pytest.ini` | 升级时**覆盖** |
| `.env.example` | `<PROJECT_ROOT>/.env`（首次部署，已存在则跳过） | **不覆盖** |
| `.mcp.json` | `<PROJECT_ROOT>/.mcp.json` | 升级时**覆盖** |
| `requirements.txt` | `<PROJECT_ROOT>/requirements.txt` | 升级时**覆盖** |

## 必读：用户责任

- `.env` 严禁提交 Git（默认已在 `.gitignore`）
- 真实凭据（`TEST_DB_PASSWORD` / `ZENTAO_PASSWORD` / `WECHAT_WEBHOOK_URL` 等）只放 `.env` 或 GitHub Secrets / Jenkins Credentials
- 修改 `.env.example` 加新字段时，必须同步 `conftest.py::EnvConfig` 与 `docs/getting-started/配置清单.md`

## 同步链路（宪章同步规则）

修改本目录任一配置文件时，**必须**联动检查：

| 修改 | 同步至 |
|------|--------|
| `.env.example` 加新字段 | `conftest.py::EnvConfig` + `配置清单.md` 字段表 + `.github/workflows/*.yml` Secrets 引用 |
| `pytest.ini` 加 marker | 自动化脚本对应 `@pytest.mark.X` 必须用已注册 marker（`strict-markers` 启用） |
| `requirements.txt` 加依赖 | `部署说明.md` utils 列表 + `.github/dependabot.yml` 分组（按需）|
| `.mcp.json` 加 server | `mcp-server-impl.md` 教程 + `配置清单.md` `.mcp.json` 段 |

## 自检命令

```bash
# 验证配置完整
test -f .env && echo "✅" || echo "❌ .env 缺失"
test -f .mcp.json && echo "✅"
pytest --collect-only         # 应能收集（即使无用例）
python -c "from conftest import get_current_env; print(get_current_env())"
```
