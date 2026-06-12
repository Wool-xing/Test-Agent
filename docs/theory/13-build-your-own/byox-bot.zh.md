---
id: byox-bot
category: 13-build-your-own
level: 中级
name_zh: 从零写 Bot(Build Your Own Bot)
name_en: Build Your Own Bot
one_liner_zh: webhook / Telegram / Slack / Discord 从零;懂 gateway 测试
one_liner_en: webhook / Telegram / Slack / Discord from scratch; gateway testing foundation
authority:
  - "Telegram Bot API docs"
  - "Slack Events API docs"
  - "RFC 8259 JSON"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 5
when_to_use: webhook 测试 / gateway 平台测试 / 消息处理 / 限流测试
common_pitfall: ["不验证 webhook 签名 → 易伪造", "省略 retry 逻辑 → 丢消息"]
example: |
  Node.js 50 行 Telegram echo bot;Slack Events API Python 100 行
related_to: [byox-web-server]
reading_en: ["https://core.telegram.org/bots/api"]
---

# 对测试工作

- **gateway 测试**(本项目 runtime/gateway 8 平台):理解 webhook 校验 + 限流 + retry
- **消息回调测试**:测平台超时 / 重试策略
- **scheduler + bot**():懂 webhook 才能测自动化日报推送
- **垃圾消息防御**:bot 必测 rate-limit + 签名校验
- **bot 模拟器**:用 from-scratch bot 当测试 mock
