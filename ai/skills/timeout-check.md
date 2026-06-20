---
name: "timeout-check"
version: "1.0.0"
display_name: "超时检测"
description: "命令超时验证 — 确认操作在指定时间内完成"
author: "Test-Agent Team"
license: "MIT"
tags: ["timeout", "performance", "command"]
icon: "⏱️"
permissions:
  network: none
  filesystem: none
  shell: readonly
  packages: []
  timeout: 60
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# 超时检测

## 概述

- **做什么:** 执行命令并验证其在指定时间内完成
- **适用场景:**
  - "确认备份脚本在30秒内完成"
  - "验证数据库迁移不超过60秒"
  - "检查启动脚本的响应时间"
- **不适用场景:** 长时间运行的服务、需要交互的命令

## 快速开始

```bash
tagent "确认 health-check.sh 在10秒内完成"
tagent "验证数据导出不超过60秒"
```

## 输入参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| command | string | 是 | - | 要执行的命令 |
| timeout | int | 否 | 30 | 超时时间(秒), 1-3600 |

## 安全

- 不使用 shell=True（已修复命令注入漏洞）
- 使用 shlex.split 安全解析命令参数
- timeout 上限 3600 秒

## 输出格式

```json
{
  "ok": true,
  "command": "echo hello",
  "elapsed_ms": 16,
  "timeout_ms": 5000,
  "exit_code": 0,
  "stdout": "hello\n"
}
```

## 错误码

| 错误码 | 说明 | 建议 |
|--------|------|------|
| TOUT-001 | 命令超时 | 增加 timeout 或优化命令 |
| TOUT-002 | 命令执行失败 | 检查命令路径和权限 |
