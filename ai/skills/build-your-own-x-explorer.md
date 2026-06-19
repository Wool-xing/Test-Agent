---
name: build-your-own-x-explorer
description: Build-your-own-X 教学引导 Skill。按用户当前测试场景推荐对应 byox 教程深度学习路径;每条标 estimated_time_hours;  教学层 13 大类落地。
tools: Read, Write, Grep, Glob
SKILL_IMPL_STATUS: production
---

# build-your-own-x-explorer

## 触发

- 用户在 learn mode 下问"为什么这么测?"+ 答案触及底层(DB/网络/正则/解析)
- 用户主动 `/build-your-own-x-explorer` 探索
- darwin-skill 检测 KB confidence=medium 卡 → 推荐 deep-dive

## 流程

1.**识别用户场景**:从最近 run / 当前 query 提取关键概念(`SQL injection` / `flaky test` / `slow regex` 等)
2.**查 KB 13-build-your-own**:`tutor.theory_kb` 找匹配卡
3.**筛选**:

   - 若用户预算 `time_hours < 5` → 仅推荐 ≤10h 短卡
   - 若 ≥20h → 推荐 P0 深度卡

4.**输出推荐 + 警告**:
   ```
   🎓 你测的是 SQL injection,推荐 deep-dive:

   ⭐ byox-database (30h) — 懂 parser → 知道注入点
   ⭐ byox-regex-engine (15h) — 懂 sanitize 边界
   ⚠️  时间投入 ≥30 小时;不是必经,但理解后**测得更狠**

   要开始吗? (y/N)
   ```

5.**跟进**:用户开始 → 记 `workspace/learning/byox_progress/{user}.json` 跟进度

## 场景 → 推荐速查表

| 测试场景 | 推荐 byox 卡 |
| ---------- | ------------ |
| SQL injection / 性能 / 死锁 | byox-database |
| 弱网 / 丢包 / TIME_WAIT | byox-network-stack |
| HTTP 并发 / keep-alive | byox-web-server |
| 测试基线 / CI 慢 | byox-git |
| RAG 检索 / 推荐相关性 | byox-search-engine |
| subprocess / 信号 | byox-shell |
| ReDoS / fuzz | byox-regex-engine |
| 解析器测试 / DSL | byox-programming-language |
| E2E 调试 / 视觉回归 | byox-web-browser |
| webhook / gateway | byox-bot |

## 融合

- 教学层:本 skill 是 learn mode 深度路径入口
- Karpathy 原则 4(Goal-Driven):推荐前必问用户**时间预算**;无预算 → 拒推
- essence-watcher:byox 标 `essence_only`(默认不动 Test-Agent),需要时本 skill 主动引

## 不做

- 不强推 deep-dive(用户测试主线优先)
- 不为每个 X 建独立 skill(防 skill 数膨胀)
- 不复制 tutorial 全文(链接 + 摘要即可)
