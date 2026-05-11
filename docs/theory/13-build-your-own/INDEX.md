# 13-build-your-own 索引

> 派生自 `_精髓库/build-your-own-x.md`。
> **元-元层教学库**:从零写 X 帮测试工程师**懂底层 → 测出根因**。

## P0 测试相关 10 卡

| 卡 | 测试场景映射 |
|----|------------|
| `byox-database` | 性能 / 事务隔离 / SQL 注入根因 |
| `byox-network-stack` | 弱网 / 丢包 / RTO / 重传 |
| `byox-web-server` | HTTP / 并发 / 反向代理 / 性能基线 |
| `byox-git` | 版本控制 / 测试基线 / 回归对比 |
| `byox-search-engine` | 检索 / 索引 / RAG 测试 |
| `byox-shell` | subprocess / 信号 / 测试编排 |
| `byox-regex-engine` | 模式匹配 / 用例参数化 / fuzz |
| `byox-programming-language` | AST / parser / fuzz 测试 |
| `byox-web-browser` | 渲染 / 浏览器测试 / Playwright 底层 |
| `byox-bot` | webhook / 消息处理 / gateway 测试 |

## 横切准则

- 每卡 `estimated_time_hours` 必填(防 §27 原则 4 时间陷阱)
- confidence 默认 `medium`(tutorial 质量参差,§23 KB)
- 引用 URL 必带 1 句摘要(防链接失效)
- `essence_only` 标:不自动提议入 Test-Agent(§29 policy)

## 不收录

- P1/P2 类(AI Model/AR/Blockchain/Game 等)— 仅 _精髓库 索引 不入 KB
