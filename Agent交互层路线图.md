# Agent 交互层路线图

> 对标：Claude Code · OpenClaw · Hermes Agent
> 策略：保留测试核心，渐进补齐 Agent 交互层
> ⚠️ 临时文档，全部完成后删除

---

## 图例

- `[✓]` 已完成 · `[ ]` 待完成 · `[WIP]` 进行中
- CC = Claude Code / OC = OpenClaw / HA = Hermes Agent

---

## P0 · 基础修复

| # | 功能 | 对标 | 状态 |
|---|------|------|:--:|
| 1 | REPL 自然语言路由修复（`_handle_natural_language` Kernel API） | — | [✓] |
| 2 | 友好错误引导（`_diagnose_error` 分类提示） | — | [✓] |
| 3 | 首次使用引导（`_check_first_run` 3 步上手） | — | [✓] |
| 4 | `/model` 分离 provider + model | CC OC HA | [✓] |

---

## P1 · 体感层

| # | 功能 | 对标 | 状态 |
|---|------|------|:--:|
| 5 | 流式输出（execute_sync → generator yield） | CC OC HA | [ ] |
| 6 | MEMORY.md 持久化（跨会话记忆） | OC HA | [ ] |
| 7 | Tab 补全增强（agent/skill 名） | CC | [ ] |
| 8 | 错误交互全覆盖（所有 /command 友好提示） | CC | [ ] |
| 9 | 欢迎动画（spinner + 连接中就绪） | OC | [ ] |

---

## P2 · 能力层

| # | 功能 | 对标 | 状态 |
|---|------|------|:--:|
| 10 | IM 多渠道（Telegram / Discord / 飞书 webhook） | OC HA | [ ] |
| 11 | Sub-agent 对话触发（"帮我测试 X"→ 自动 launch） | OC HA | [ ] |
| 12 | MCP client 完善（`runtime/mcp/` 已有基础） | CC HA | [ ] |
| 13 | Heartbeat/Cron 主动任务（定时自检、推送报告） | OC HA | [ ] |
| 14 | 模型自动路由（小模型分类→大模型执行） | OC HA | [ ] |
| 15 | 多行输入（代码块、长文本粘贴） | CC | [ ] |

---

## P3 · 深度层

| # | 功能 | 对标 | 状态 |
|---|------|------|:--:|
| 16 | FTS5 会话搜索（SQLite 全文索引） | HA | [ ] |
| 17 | Context 智能压缩（长对话自动总结） | HA CC | [ ] |
| 18 | 技能自进化（自动创建/评分 Skill） | HA | [ ] |
| 19 | 7×24 daemon 模式（`tagent serve --daemon`） | OC | [ ] |
| 20 | 用户画像 USER.md（自动学习偏好） | OC HA | [ ] |
| 21 | Smart Approvals（学习信任命令） | HA | [ ] |
| 22 | 插件 drop-in（`plugins/` 热加载） | OC HA | [ ] |
| 23 | Voice mode（PTT CLI + Telegram voice notes） | HA | [ ] |

---

## 架构原则

```
不改测试核心（16 Experts + 32 Skills + 79 Utils + Prefect 编排）
只在上面加 Agent 交互层。

  ┌──────────────────────────┐
  │   Agent 交互层 (新增)     │  ← P1-P3
  │   REPL · IM · Memory     │
  ├──────────────────────────┤
  │   测试编排层 (已有)       │  ← 不动
  │   test-coordinator · DAG │
  ├──────────────────────────┤
  │   执行引擎层 (已有)       │  ← 不动
  │   runtime · utils · CLI  │
  └──────────────────────────┘
```

## 修改纪律

每次修改遵守 Karpathy 四纪律：
1. 先想再写 — 查根因、列假设
2. 简单优先 — 最小代码，不复用不抽象
3. 手术修改 — 只改必须改，匹配现有风格
4. 目标驱动 — 每行可追溯到任务
