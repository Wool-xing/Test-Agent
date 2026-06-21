---
name: demo-http
version: 1.0.0
display_name: Demo HTTP Check
description: Example skill — check HTTP endpoint health (status code, response time)
permissions:
  network: restricted
  filesystem: none
  shell: none
  timeout: 30
tags: [http, demo, monitoring]
icon: "🌐"
compatible:
  platforms: [windows, macos, linux]
  modes: [community, enterprise]
---

# Demo HTTP Check

## Overview

Simple HTTP health check skill. Checks that a URL returns the expected status code
within a time limit. Good starting point for learning Skill development.

## Quick Start

```bash
# Install
tagent skill install examples/skills/demo-http

# Use
tagent "check if https://example.com is up"
tagent "verify https://api.example.com/health returns 200"
tagent "is https://example.com responding within 2 seconds"
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| url | string | yes | - | Target URL (must start with http:// or https://) |
| expected_status | int | no | 200 | Expected HTTP status code |
| timeout | int | no | 10 | Timeout in seconds (1-30) |

## Output Format

```json
{
  "status": "pass",
  "summary": "https://example.com returned 200 in 230ms",
  "details": {
    "url": "https://example.com",
    "status_code": 200,
    "response_time_ms": 230
  },
  "checks": [
    {"name": "Status Code", "expected": 200, "actual": 200, "pass": true},
    {"name": "Response Time", "expected": "<10s", "actual": "230ms", "pass": true}
  ],
  "error": null
}
```

## Error Codes

| Code | Description | User Action |
|------|-------------|-------------|
| HTTP-001 | Invalid URL format | Check URL starts with http:// or https:// |
| HTTP-002 | Connection timeout | Check network/firewall, increase timeout |
| HTTP-003 | DNS resolution failed | Check domain name spelling |

## Testing

```bash
tagent skill test demo-http
```
