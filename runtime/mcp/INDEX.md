# mcp 索引

> 主宪章 §16 预留 6 件套,V1.2.0(M2)实现。
> 当前 `config/.mcp.json` 仅启用 filesystem;本目录服务通过 `config/.mcp.json` 启用。

## 模块清单

| MCP server | 路径 | 工具(tools) |
|------------|------|-------------|
| test-orchestrator | `test_orchestrator/` | catalog / run / status / report / plan |
| protocol-adapter | `protocol_adapter/` | http / grpc / ws / mqtt / kafka 各 send/recv |
| evidence-vault | `evidence_vault/` | upload_evidence / list_evidence / get_evidence / search_evidence |
| defect-tracker | `defect_tracker/` | create_bug / update_bug / query_bugs / link_to_case |
| knowledge-base | `knowledge_base/` | index_case / search_similar_cases / index_defect / search_similar_defects |
| compliance-checker | `compliance_checker/` | check_compliance(profile, evidence_run_id) |

## 启用方式

每个 server 可独立启动:

```bash
python -m runtime.mcp.test_orchestrator.server     # stdio mode
python -m runtime.mcp.test_orchestrator.server --http 8801  # http mode
```

或注册到 `config/.mcp.json`:

```json
{
  "mcpServers": {
    "test-orchestrator": {
      "command": "python",
      "args": ["-m", "runtime.mcp.test_orchestrator.server"]
    }
  }
}
```

## 共享基类

`base.py` 提供:
- `make_server(name, version)`:统一 Server 实例化
- `tool_decision_logged(name)`:工具装饰器,自动落 `decisions/{date}_mcp_{tool}.json`(宪章 §18-12)
- `with_run_id(handler)`:run_id 全链路注入(§21 横切可复现性)

## MCP 客户端 (P2 #12)

`client.py` 提供:
- `McpClient`: 连接本地 MCP 服务器(stdio), 发现工具, 调用工具
- `get_client()`: 单例全局实例
- 自动读取 `config/.mcp.json` 获取服务器配置
