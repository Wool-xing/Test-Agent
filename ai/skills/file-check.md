---
name: "file-check"
version: "1.0.0"
display_name: "文件检测"
description: "文件存在性/大小/内容验证 — 检查文件是否符合预期"
author: "Test-Agent Team"
license: "MIT"
tags: ["file", "validation", "content", "size"]
icon: "📄"
permissions:
  network: none
  filesystem: read
  shell: none
  packages: []
  timeout: 10
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# 文件检测

## 概述

- **做什么:** 检查文件是否存在、大小是否符合范围、内容是否包含指定文本
- **适用场景:**
  - "检查配置文件是否存在"
  - "验证日志文件大小不超过100MB"
  - "确认输出文件包含 'SUCCESS'"
- **不适用场景:** 二进制文件内容检测、大文件(>100MB)全文搜索

## 快速开始

```bash
tagent "检查 workspace/output.json 是否存在"
tagent "验证日志文件大小"
```

## 输入参数

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| path | string | 是 | - | 文件路径（项目根相对路径） |
| min_size | int | 否 | 0 | 最小字节数 |
| max_size | int | 否 | 0 | 最大字节数 |
| content_contains | string | 否 | "" | 文件中应包含的文本 |

## 安全

- 路径自动解析并限制在项目根目录内
- 阻止路径穿越攻击（../../../etc/passwd）
- 仅允许读取项目内文件

## 输出格式

```json
{
  "ok": true,
  "path": "workspace/output.json",
  "exists": true,
  "size": 1234,
  "checks": [
    {"check": "min_size", "expected": ">100", "actual": "1234", "pass": true}
  ]
}
```

## 错误码

| 错误码 | 说明 | 建议 |
|--------|------|------|
| FILE-001 | 文件不存在 | 检查路径是否正确 |
| FILE-002 | 路径在项目外 | 只能检查项目内文件 |
| FILE-003 | 大小不满足条件 | 检查文件大小是否符合预期 |
