---
id: byox-programming-language
category: 13-build-your-own
level: 高级
name_zh: 从零写编程语言(Build Your Own Programming Language)
name_en: Build Your Own Programming Language
one_liner_zh: 词法 → 语法 → AST → eval;懂 fuzz + 编译器 bug 测试
one_liner_en: Lexer → parser → AST → eval; foundation for fuzz + compiler bug testing
authority:
  - "Crafting Interpreters(Bob Nystrom,开源)"
  - "《Compilers: Principles, Techniques, and Tools》(Dragon Book)"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
estimated_time_hours: 80
when_to_use: fuzz 测试 / AST 解析 / DSL 测试 / 编译器测试
common_pitfall: ["跳过 lexer 直接写 parser → 不能学 token", "不学 AST 优化 → 不能学性能 regression"]
example: |
  Lox 解释器(Crafting Interpreters)200 页 → tree-walk interpreter + bytecode VM
related_to: [byox-regex-engine, byox-shell]
reading_en: ["https://craftinginterpreters.com/"]
---

# 对测试工作

- **fuzz 测试**:懂 AST → 生成结构化随机输入(grammar-based fuzz)
- **DSL 测试**:测试配置语言 / 业务规则引擎
- **编译器 bug**:测试代码生成正确性(差分测试)
- **解析器测试**:本项目 `runtime/router/schema.py` 用 Pydantic 解析 LLM JSON,理解 grammar 才能写好 schema
- **ECC agent-introspection-debugging** 调试 LLM 输出 = 解析 LLM 类自然语言"DSL"
