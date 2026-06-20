---
name: "ping-check"
version: "1.0.0"
display_name: "Ping 延迟检测"
description: "ICMP ping 延迟测试 — 检测主机可达性和网络延迟"
author: "Test-Agent Team"
license: "MIT"
tags: ["network", "ping", "latency", "connectivity"]
icon: "📡"
permissions:
  network: restricted
  filesystem: none
  shell: readonly
  packages: []
  timeout: 30
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# Ping 延迟检测

## 概述

- **做什么:** 通过 ICMP ping 检测目标主机是否可达，测量网络延迟
- **适用场景:**
  - "检查服务器 192.168.1.1 是否在线"
  - "测一下网关的延迟"
  - "验证数据库服务器连通性"
- **不适用场景:** HTTP 服务检测（用 http-check），端口检测

## 快速开始

```bash
tagent "ping 一下 127.0.0.1"
tagent "检查 192.168.1.1 的网络延迟"
```

## 输入参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| host | string | 是 | - | 目标主机名或IP |
| count | int | 否 | 4 | ping 次数，1-100 |
| timeout | int | 否 | 30 | 超时(秒) |

## 输出格式

```json
{
  "ok": true,
  "host": "127.0.0.1",
  "latency_ms": 11,
  "output": "ping statistics..."
}
```

## 错误码

| 错误码 | 说明 | 建议 |
|--------|------|------|
| NET-001 | 无效主机名 | 检查主机名格式 |
| NET-002 | ping 超时 | 增加 timeout 或检查防火墙 |
