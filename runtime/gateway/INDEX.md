# gateway 索引

> 单 gateway 进程多平台,Agent**不绑笔记本**。

## 平台清单(M3-5 起步 8 平台,可扩到 20+)

| 平台 | 文件 | 触发 |
| ------ | ------ | ------ |
| Telegram | `platforms/telegram.py` | Bot API ↔ |
| Discord | `platforms/discord.py` | Bot API ↔ |
| Slack | `platforms/slack.py` | Webhook → |
| 微信 | `platforms/wechat.py` | Webhook→ + API ↔ |
| 飞书 | `platforms/feishu.py` | Webhook+Bot ↔ |
| 钉钉 | `platforms/dingtalk.py` | Webhook→ + API ↔ |
| QQ Bot | `platforms/qqbot.py` | Bot API ↔ |
| Email | `platforms/email.py` | SMTP → |
| 通用 Webhook | `platforms/webhook.py` | HTTP POST → |

> ↔ = 双向(收发) · → = 单向(仅发) · 收消息走 `runtime/api/endpoints/webhooks.py`

未来扩(留扩展位):WhatsApp / Signal / SMS / iMessage(bluebubbles)/ Matrix / Mattermost / HomeAssistant / Yuanbao / 元宝

## 桥接层 (P2 #10)

| 模块 | 文件 | 用途 |
| ------ | ------ | ------ |
| IM→Agent 桥 | `bridge.py` | 入站消息 → Kernel 路由 → 格式化 → 平台回复 |

Webhook 端点: `runtime/api/endpoints/webhooks.py` (Telegram / Discord / 飞书 / 企微 / 钉钉 / QQ Bot)

## 规则

-**单 session 跨平台**:用户在 Telegram 开话题,Slack 续话不丢上下文
-**统一 base 抽象**:`Platform` 接口,所有平台实现 `send` / `configure`
-**运行时 prompt 注入扫**(继承 scheduler 同模块)
-**delivery 走 scheduler**:cron 任务输出 → 推送对应平台
