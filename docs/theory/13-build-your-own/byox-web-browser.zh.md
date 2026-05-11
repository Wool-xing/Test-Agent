---
id: byox-web-browser
category: 13-build-your-own
level: 高级
name_zh: 从零写浏览器(Build Your Own Web Browser)
name_en: Build Your Own Web Browser
one_liner_zh: HTML/CSS parse + layout + paint;懂 Playwright/Selenium 底层
one_liner_en: HTML/CSS parse + layout + paint; foundation of Playwright/Selenium
authority:
  - "Browser Engineering(Pavel Panchekha,Python from-scratch)"
  - "WHATWG HTML Living Standard"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 60
when_to_use: E2E 测试根因 / 视觉回归 / Web Vitals / Playwright selector 失效调试
common_pitfall: ["不实现 event loop → 不懂 async 测试", "省略 JS engine → 不懂 SPA 测试"]
example: |
  Python "Browser Engineering" 书 → HTML parser → CSS → layout → text paint
related_to: [byox-web-server, byox-network-stack]
reading_en: ["https://browser.engineering/"]
---

# 对测试工作

- **E2E 测试调试**:Playwright `wait_for_load_state` 失败 → 懂浏览器 event loop 才能定位
- **视觉回归**:理解 layout/paint → 知道为什么字体抖动 / DPR / 动画导致 SSIM 不稳
- **Web Vitals**(LCP/FID/CLS/INP):懂渲染管线才能优化
- **selector 失效**(M1-10 web-demo bug):懂 DOM 才知道用 `role` / `text` 而非 CSS class
- **§28 ECC e2e-testing skill** 落地的底层
