---
id: byox-regex-engine
category: 13-build-your-own
level: 高级
name_zh: 从零写正则引擎(Build Your Own Regex Engine)
name_en: Build Your Own Regex Engine
one_liner_zh: NFA/DFA from scratch;懂 ReDoS 攻击 + fuzz 测试
one_liner_en: NFA/DFA from scratch; understand ReDoS + fuzz testing
authority:

  - "Russ Cox《Regular Expression Matching Can Be Simple And Fast》经典"
  - "OWASP ReDoS"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 15
when_to_use: ReDoS 攻击 / fuzz 用例生成 / 字符串测试 / log parser 测试
common_pitfall: ["仅写 backtracking → 易 ReDoS(catastrophic backtracking)", "不学 NFA → 不能并行匹配"]
example: |
  Russ Cox C 30 行 NFA matcher;对比 Python re(backtracking)在 (a+)+ 上的性能差异
related_to: [byox-programming-language]
reading_en: ["https://swtch.com/~rsc/regexp/regexp1.html"]
---

# 对测试工作

-**ReDoS 攻击**(OWASP API4):懂 backtracking 才能识别 vulnerable regex
-**fuzz 用例**:懂 regex → 写更精准的 invalid 输入生成器
-**log parser 测试**:测大日志解析性能;NFA vs backtracking 差几个数量级
-**OWASP A03 Injection**:正则参与 sanitize 时不安全的 escape
