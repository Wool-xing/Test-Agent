---
id: http-https
category: 06-protocols
level: 基础
name_zh: HTTP / HTTPS 协议
name_en: HTTP / HTTPS
one_liner_zh: Web 通信底座;90% Web/API 测试的协议起点
one_liner_en: Web communication foundation; starting point for 90% of Web/API tests
authority:
  - "RFC 9110-9114(HTTP/1.1, HTTP/2, HTTP/3 现行 RFC)"
  - "MDN Web Docs HTTP"
  - "OWASP API Security Top 10 2023"
  - ISTQB Foundation §6.3.3 API 测试
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: REST API / Web 系统 / 浏览器 / 移动 H5 / Webhook / 第三方接口 — 必测
common_pitfall:
  - "只测 200,不测 4xx/5xx"
  - "不测幂等性(POST 重复提交)"
  - "不测 TLS 版本+证书+SNI"
  - "不测 keep-alive 长连接行为"
  - "不测大体积 payload(超限/截断)"
example: |
  ```python
  import requests

  resp = requests.post
      "https://api.example.com/v1/orders",
      json={"sku": "X1", "qty": 1},
      headers={"Idempotency-Key": "uuid-xxx"},
      timeout=10,
  )
  assert resp.status_code == 201
  assert resp.headers.get("X-Request-Id")
  ```
related_to: [grpc, websocket, quic-http3, rest-api, openapi]
reading_zh:
  - "阮一峰博客《HTTP/2 笔记》"
  - "RFC 9110 中文译本"
reading_en:
  - https://datatracker.ietf.org/doc/html/rfc9110
  - https://developer.mozilla.org/en-US/docs/Web/HTTP
---

# HTTP / HTTPS

Web/API 测试**必经协议**。Test-Agent `utils/api_retry_util.py` 提供 10/20/40s 指数退避;`runtime/mcp/protocol_adapter/adapters.py` 的 `HTTPAdapter` 直接可用。

## 必测维度

| 维度 | 工具 |
| ------ | ------ |
| 状态码 | requests + assert |
| Header | TLS 版本 / Cache-Control / CORS / Cookie |
| Body | JSON/XML schema 校验 |
| 性能 | TTFB / P95 / TPS(JMeter / k6) |
| 安全 | OWASP API Top 10 / TLS 配置 |
| 幂等性 | Idempotency-Key 重复提交 |
| 重试 | 指数退避 |

## 为什么 Agent 默认调 HTTP?

被测物 = Web/REST/GraphQL/Webhook/SOAP → 全部跑在 HTTP 之上;Agent 用 `runtime/mcp/protocol_adapter` 的 HTTP adapter 做协议层抽象。
