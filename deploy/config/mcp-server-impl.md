# MCP Server 自实现教程

> **当前状态**：`.mcp.json` 仅启用 filesystem。zentao / wechat / feishu / dingtalk 通知与 Bug 提交走 SDK/curl 直连（utils/）。本文档提供 4 个 mcp_server 自实现骨架，按需启用。

---

## 1. 何时需要自实现 MCP server？

| 场景 | 推荐方案 |
|------|---------|
| 项目用 Claude Code 单机开发，只需 utils 调用 | **不需要 MCP**，当前直连方案足够 |
| 团队多个开发者，希望 Claude Code 直接通过 MCP 调用 BugTracker/通知 | 实现对应 mcp_server |
| 需要 Claude Code agent 主动查询 Bug 状态、读取 webhook 历史 | 实现对应 mcp_server |
| 与其他工具（Cursor / Continue.dev）共享 MCP 通道 | 实现 mcp_server（MCP 跨工具标准） |

---

## 2. MCP 协议规范

参考：
- 官方文档：https://modelcontextprotocol.io
- Python SDK：`pip install mcp`（或 `pip install anthropic-mcp`）
- TypeScript SDK：`@modelcontextprotocol/sdk`

MCP server 通常通过 stdio 与 client 通信，对外暴露 tools / resources / prompts 三类能力。

---

## 3. 实现骨架（Python）

### 3.1 通用结构

```python
# zentao_mcp_server/__main__.py
"""禅道 MCP Server 骨架（默认 BugTracker 实现示例;Jira/GitHub/GitLab/Linear/Webhook 同骨架,主宪章 §12）"""
import asyncio
import json
import logging
import os
import sys
from typing import Any

# 安装：pip install mcp
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# 复用项目 utils
sys.path.insert(0, os.environ.get("PROJECT_ROOT", "."))
from utils.zentao_bug_manager import ZentaoBugManager, SEVERITY_MAP

server = Server("zentao-mcp")
logger = logging.getLogger(__name__)

manager: ZentaoBugManager | None = None


def get_manager() -> ZentaoBugManager:
    global manager
    if manager is None:
        manager = ZentaoBugManager()
    return manager


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="zentao_create_bug",
            description="提交 Bug 到禅道（默认 BugTracker;其他 adapter 同 tool schema）",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "product": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                    "steps": {"type": "string"},
                    "buildFound": {"type": "string"},
                },
                "required": ["title", "product", "severity", "steps"],
            },
        ),
        types.Tool(
            name="zentao_get_bug",
            description="查询 Bug 详情",
            inputSchema={
                "type": "object",
                "properties": {"bug_id": {"type": "integer"}},
                "required": ["bug_id"],
            },
        ),
        types.Tool(
            name="zentao_list_bugs",
            description="按产品查询活跃 Bug",
            inputSchema={
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "status": {"type": "string", "default": "active"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["product_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    mgr = get_manager()
    try:
        if name == "zentao_create_bug":
            severity_str = arguments.pop("severity")
            arguments["severity"] = SEVERITY_MAP[severity_str]
            arguments.setdefault("pri", arguments["severity"])
            result = mgr.create_bug(arguments)
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        if name == "zentao_get_bug":
            result = mgr.get_bug(arguments["bug_id"])
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        if name == "zentao_list_bugs":
            bugs = mgr.list_bugs(**arguments)
            return [types.TextContent(type="text", text=json.dumps(bugs, ensure_ascii=False, indent=2))]

        raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.exception(name)
        return [types.TextContent(type="text", text=f"❌ {type(e).__name__}: {e}")]


async def main():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read, write,
            InitializationOptions(
                server_name="zentao-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### 3.2 wechat_mcp_server 骨架

```python
# wechat_mcp_server/__main__.py
import asyncio, json, logging
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types
from utils.generate_report import send_wechat_report

server = Server("wechat-mcp")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="wechat_send_report",
            description="发送测试报告到企业微信群",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                    "environment": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["通过", "失败"]},
                    "pass_rate": {"type": "number"},
                    "p0_bugs": {"type": "integer"},
                    "report_url": {"type": "string"},
                },
                "required": ["project", "verdict", "pass_rate"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name, args):
    if name == "wechat_send_report":
        ok = send_wechat_report(args)
        return [types.TextContent(type="text", text="✅ 已发送" if ok else "❌ 发送失败")]
    raise ValueError(name)


async def main():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, ...)


if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 feishu / dingtalk 同模式

复用 `utils/generate_report.send_feishu_report` / `send_dingtalk_report`，结构与 wechat 一致。

---

## 4. 启用配置

实现完成后，更新 `.mcp.json`：

```json
{
  "_comment": "...",
  "mcpServers": {
    "filesystem": { "command": "npx", "args": [...] },

    "zentao": {
      "command": "python",
      "args": ["-m", "zentao_mcp_server"],
      "env": {
        "PROJECT_ROOT": "${PROJECT_ROOT:-.}",
        "ZENTAO_BASE_URL": "${ZENTAO_BASE_URL}",
        "ZENTAO_ACCOUNT": "${ZENTAO_ACCOUNT}",
        "ZENTAO_PASSWORD": "${ZENTAO_PASSWORD}"
      },
      "description": "禅道 Bug 管理 MCP（默认 BugTracker;Jira/GitHub/GitLab/Linear/Webhook 同 MCP 接口）"
    },
    "wechat": {
      "command": "python",
      "args": ["-m", "wechat_mcp_server"],
      "env": {
        "PROJECT_ROOT": "${PROJECT_ROOT:-.}",
        "WECHAT_WEBHOOK_URL": "${WECHAT_WEBHOOK_URL}"
      },
      "description": "企业微信通知 MCP"
    },
    "feishu":   { /* 类似 */ },
    "dingtalk": { /* 类似 */ }
  }
}
```

---

## 5. 包结构建议

```text
your-test-project/
└── mcp_servers/                    # 新建目录
    ├── zentao_mcp_server/
    │   ├── __init__.py
    │   └── __main__.py
    ├── wechat_mcp_server/
    │   └── __main__.py
    ├── feishu_mcp_server/
    │   └── __main__.py
    └── dingtalk_mcp_server/
        └── __main__.py
```

`PYTHONPATH` 指向 `mcp_servers/` 或安装为 editable package：

```bash
pip install -e mcp_servers/zentao_mcp_server
```

---

## 6. requirements.txt 追加（仅启用 MCP server 时）

```text
mcp>=0.9.0          # 或 anthropic-mcp，按 SDK 选择
```

---

## 7. 调试

### 7.1 stdio 直接测试

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m zentao_mcp_server
```

### 7.2 通过 Claude Code 验证

```bash
claude mcp list                  # 列出已加载 server
claude /mcp                       # 打开 MCP 面板
# 在对话中调用："调 zentao_create_bug 提交一个测试 Bug"
```

### 7.3 日志

```python
import logging
logging.basicConfig(
    filename="workspace/测试报告/{项目名}/mcp-zentao.log",
    level=logging.DEBUG,
)
```

---

## 8. 与直连方案的取舍

| 维度 | MCP 通道 | SDK/curl 直连（当前默认） |
|------|---------|--------------------------|
| 上手成本 | 高（需实现 mcp_server） | 低（utils 已就绪） |
| 工具自治 | 强（Claude Code agent 可主动调） | 弱（需在 agent prompt 中说明步骤） |
| 跨工具复用 | ✅ 任意 MCP client 共享 | ❌ 仅当前 Python 项目 |
| 性能 | 略高（stdio + JSON-RPC） | 直连最快 |
| 可观测性 | MCP 日志独立 | 与项目 utils 日志混合 |
| CI/CD 适用 | ⚠️ MCP 需 Claude 进程，CI 不便 | ✅ utils 直接 import 调用 |

**结论**：日常用直连足够。**MCP 通道适合 Claude Code 交互场景**（手动调试、问答、agent 协调）。CI/CD 仍走直连。

---

## 9. 现成 MCP Server 参考

社区已有部分通用 MCP server，可参考：

- `@modelcontextprotocol/server-filesystem`（已启用）
- `@modelcontextprotocol/server-git`
- `@modelcontextprotocol/server-postgres`
- `@modelcontextprotocol/server-slack`
- 第三方 zentao MCP（社区有少量实现，需自行评估稳定性）

未找到现成的就按本文骨架自实现。
