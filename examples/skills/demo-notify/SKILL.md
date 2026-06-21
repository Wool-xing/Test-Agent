---
name: demo-notify
version: 1.0.0
display_name: Demo Notify
description: Example skill — send test notifications to configured channels
permissions:
  network: restricted
  filesystem: read
  shell: none
  timeout: 15
tags: [notification, demo, integration]
icon: "🔔"
---

# Demo Notify

Send a test notification to verify notification channel configuration.

```bash
tagent skill install examples/skills/demo-notify
tagent "send a test notification to Slack"
tagent "notify #alerts channel that deployment is complete"
```
