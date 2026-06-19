---
id: byox-web-server
category: 13-build-your-own
level: 中级
name_zh: 从零写 Web 服务器(Build Your Own Web Server)
name_en: Build Your Own Web Server
one_liner_zh: HTTP 1.1 + 多路复用;懂并发/keep-alive/反向代理
one_liner_en: HTTP/1.1 + multiplexing; concurrency/keep-alive/reverse proxy
authority:

  - "RFC 9110-9114 现行 HTTP 标准"
  - "Beej's Guide / 多个 from-scratch tutorials"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 15
when_to_use: 性能基线 / 并发测试 / keep-alive 行为 / 反向代理调优
common_pitfall: ["简化版不实现 chunked transfer", "省略 Host header → HTTP/1.1 必须"]
example: |
  Python asyncio 实现简单 HTTP/1.1 + epoll;每连接 keep-alive 10 秒
related_to: [byox-database, byox-network-stack]
reading_en: ["http://aosabook.org/en/500L/a-simple-web-server.html"]
---

# 对测试工作

-**并发测试**:懂事件循环 / 线程池 / async → 设计负载
-**keep-alive**:测试 long-polling / SSE / 连接复用
-**反向代理 / WAF**:理解 nginx 转发头 X-Forwarded-* 测注入
-**TCP 半关闭**:理解 close vs shutdown → 测优雅关闭
