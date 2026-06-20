---
name: "process-check"
version: "1.0.0"
display_name: "进程检测"
description: "进程运行状态检测 — 验证指定进程是否在运行"
author: "Test-Agent Team"
license: "MIT"
tags: ["process", "monitoring", "system"]
icon: "⚙️"
permissions:
  network: none
  filesystem: none
  shell: readonly
  packages: []
  timeout: 10
SKILL_IMPL_STATUS: production
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# 进程检测

## 概述

- **做什么:** 检测指定进程是否正在运行
- **适用场景:**
  - "确认 nginx 是否在运行"
  - "检查数据库进程是否存在"
  - "验证 worker 进程存活"
- **不适用场景:** 进程资源使用检测、进程性能分析

## 快速开始

```bash
tagent "检查 python 进程是否在运行"
tagent "确认 nginx 进程存活"
```

## 输入参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| name | string | 是 | - | 进程名称 |
| expected_running | bool | 否 | true | 期望状态 |

## 安全

- 仅允许字母数字和 . _ - 字符的进程名
- 不允许管道/重定向等 shell 特殊字符
- 使用 tasklist (Windows) / pgrep (Unix) 检测

## 输出格式

```json
{
  "ok": true,
  "process": "python",
  "running": true,
  "expected_running": true
}
```

## 错误码

| 错误码 | 说明 | 建议 |
|--------|------|------|
| PROC-001 | 进程名包含非法字符 | 仅使用字母数字和 . _ - |
| PROC-002 | 进程未运行(期望运行) | 检查进程是否已启动 |
| PROC-003 | 进程在运行(期望停止) | 检查是否需要停止进程 |
