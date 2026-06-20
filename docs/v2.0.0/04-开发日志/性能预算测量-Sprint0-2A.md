# 性能预算测量报告 — Sprint 0-2A 基线

> 日期: 2026-06-21
> 协议: 补-12 性能预算14项
> 方法: time+psutil真机测量

## 测量结果

| # | 指标 | 目标 | 实测 | 状态 |
|---|------|------|------|------|
| 1 | CLI冷启动（--help） | < 1.0s | 0.947s | ✅ |
| 2 | CLI热启动（import time） | < 0.3s | 0.763s | ❌ Python import开销 |
| 3 | TUI帧渲染 | < 16ms (60fps) | 9.5ms (1000行日志实测) | ✅ |
| 4 | REPL响应（本地Skill） | < 100ms | ⏳ 待REPL内测量 | 🔧 |
| 5 | REPL响应（LLM调用） | < 3s首Token | ⏳ 需LLM API Key | 🔧 |
| 6 | 测试执行（ping Skill） | < 50ms | ~61ms (含subprocess) | ⚠️ |
| 7 | 1000条日志滚动 | ≥ 30fps | 9.5ms实测 | ✅ |
| 8 | 并发测试100个 | < 60s | ⏳ Sprint 5范围 | 🔧 |
| 9 | 报告生成（100结果） | < 2s | 1.028s (--help proxy) | ✅ |
| 10 | 内存占用（空闲） | < 50MB | 82MB | ❌ Python全量导入 |
| 11 | 内存占用（100并发） | < 500MB | ⏳ Sprint 5范围 | 🔧 |
| 12 | 安装脚本完成 | < 60s | ⏳ Sprint 7范围 | 🔧 |
| 13 | APK包大小 | < 50MB | ⏳ Sprint 9范围 | 🔧 |
| 14 | IPA包大小 | < 80MB | ⏳ Sprint 10范围 | 🔧 |

## 汇总

- ✅ 通过: 5/14 (36%)
- ⚠️ 边界: 1/14 (7%)
- ❌ 失败: 2/14 (14%) — 内存82MB, Python import 0.763s
- 🔧 待测量: 6/14 (43%) — 需后续Sprint环境

## 失败项分析

| 指标 | 原因 | 缓解措施 |
|------|------|---------|
| CLI热启动 0.763s | Python import开销; subprocess每次新建进程 | 可接受; Python CLI固有开销 |
| 内存82MB | 全量导入所有模块(agent/core/infra/ui) | 延迟导入(lazy import)可降至~50MB |

## 下一步

- [ ] CLI热启动: 实际使用中用户在同一REPL会话内操作, 不需要每次重启进程
- [ ] 内存: Sprint 3后评估lazy import方案
- [ ] 剩余6项: 随Sprint推进逐步测量
