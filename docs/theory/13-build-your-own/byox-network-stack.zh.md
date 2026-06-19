---
id: byox-network-stack
category: 13-build-your-own
level: 高级
name_zh: 从零写网络栈(Build Your Own Network Stack)
name_en: Build Your Own Network Stack
one_liner_zh: TCP from scratch;懂丢包/重传/RTO/拥塞控制
one_liner_en: TCP from scratch; understand loss/retx/RTO/congestion
authority:

  - "RFC 9293(TCP 现行)"
  - "Beej's Guide to Network Programming"
  - "多个 saminiir/level-ip 等 TCP-from-scratch"
confidence: medium
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 40
when_to_use: 弱网测试 / 丢包模拟 / 网络分区 / RTO 调优 / 长连接稳定性 根因
common_pitfall:

  - tutorial 多在用户态(tun/tap),忽略硬件中断 / DMA
  - 简化版不实现拥塞控制 → 不能学 CUBIC/BBR
example: |
  Linux tun/tap 上写 TCP echo;handshake + slow start + retx
related_to: [byox-web-server, byox-database]
reading_zh: ["阮一峰《TCP/IP 详解 卷一 协议》笔记"]
reading_en: ["https://saminiir.com/lets-code-tcp-ip-stack-1/"]
---

# 从零写网络栈

## 对测试工作

-**弱网模拟**:tc + netem 是黑盒;懂栈才知道哪里能注入丢包
-**超时调优**:理解 RTO 计算 / 退避算法 → 调测试 timeout
-**TIME_WAIT**:大并发后端口耗尽根因
-**Nagle / Delayed ACK**:小包性能差根因
-**TLS over TCP**:Handshake 慢的多种原因
