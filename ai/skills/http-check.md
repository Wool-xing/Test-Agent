---
name: "http-check"
version: "1.0.0"
display_name: "HTTP 端点检测"
description: "HTTP/HTTPS 端点健康检查 — 验证状态码、响应时间"
author: "Test-Agent Team"
license: "MIT"
tags: ["http", "web", "api", "health-check"]
icon: "🌐"
permissions:
  network: restricted
  filesystem: none
  shell: none
  packages: []
  timeout: 30
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# HTTP 端点检测

## 概述

- **做什么:** 向 HTTP/HTTPS URL 发送请求，验证返回状态码和响应时间
- **适用场景:**
  - "检查 https://api.example.com/health 是否正常"
  - "验证登录页面返回 200"
  - "监测 API 端点响应时间"
- **不适用场景:** WebSocket、gRPC、非HTTP协议

## 快速开始

```bash
tagent "检查 www.example.com 是否正常响应"
tagent "测一下 https://api.example.com/health 的状态码"
```

## 输入参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| url | string | 是 | - | 目标URL (仅http/https) |
| method | enum(GET,POST,HEAD) | 否 | GET | HTTP方法 |
| expected_status | int | 否 | 200 | 期望状态码 |
| timeout | int | 否 | 30 | 超时(秒) |

## 安全

- 仅允许 http/https 协议
- 阻止访问私有/内部IP (10.x, 192.168.x, 127.x, 169.254.x)
- 阻止 file://, gopher:// 等非HTTP协议
- 不跟随重定向到内部IP

## 输出格式

```json
{
  "ok": true,
  "url": "https://www.example.com",
  "status_code": 200,
  "expected_status": 200,
  "response_time_ms": 230,
  "body_size": 1234
}
```

## 错误码

| 错误码 | 说明 | 建议 |
|--------|------|------|
| HTTP-001 | URL格式无效 | 检查URL是否以 http:// 或 https:// 开头 |
| HTTP-002 | 私有IP被拦截 | 目标不能是内部/私有地址 |
| HTTP-003 | 不支持的协议 | 仅支持 http/https |
| HTTP-004 | DNS解析失败 | 检查域名是否正确 |
| HTTP-005 | 连接超时 | 增加 timeout 或检查防火墙 |
