# gateway 索引

> 单 gateway 进程多平台,Agent **不绑笔记本**。

## 平台清单(M3-5 起步 8 平台,可扩到 20+)

| 平台 | 文件 | 触发 |
|------|------|------|
| Telegram | `platforms/telegram.py` | Bot API |
| Discord | `platforms/discord.py` | Bot API |
| Slack | `platforms/slack.py` | Webhook/Bot |
| 微信 | `platforms/wechat.py` | Webhook |
| 飞书 | `platforms/feishu.py` | Webhook+Bot |
| 钉钉 | `platforms/dingtalk.py` | Webhook |
| Email | `platforms/email.py` | SMTP+IMAP |
| 通用 Webhook | `platforms/webhook.py` | HTTP POST |

未来扩(留扩展位):企微 / WhatsApp / Signal / SMS / QQ / iMessage(bluebubbles)/ Matrix / Mattermost / HomeAssistant / Yuanbao / 元宝

## 规则

- **单 session 跨平台**:用户在 Telegram 开话题,Slack 续话不丢上下文
- **统一 base 抽象**:`Platform` 接口,所有平台实现 `send/recv/configure`
- **运行时 prompt 注入扫**(继承 scheduler 同模块)
- **delivery 走 scheduler**:cron 任务输出 → 推送对应平台
