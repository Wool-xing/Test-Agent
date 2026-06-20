# System Prompt 最佳实践研究报告

> **日期:** 2026-06-21
> **阶段:** 阶段 0：深度调研
> **目标:** 研究 AI Agent 项目的 System Prompt 设计模式，为 Test-Agent 的 Prompt 体系提供最佳实践

---

## 1. 核心挑战

AI Agent 的 System Prompt 与普通聊天 Prompt 有本质区别：

| 维度 | 聊天 Prompt | Agent Prompt |
|------|------------|-------------|
| 生命周期 | 单次对话 | 长会话（数百轮） |
| 目标 | 回答问题 | 自主执行任务 |
| 安全性 | 内容审核 | 操作安全（文件/网络/进程） |
| 复杂度 | 简单指令 | 多层规则 + 工具定义 + 编排 |
| 漂移风险 | 低 | 高 — 长对话中"忘记"约束 |
| 注入风险 | 低 | 极高 — 用户输入可能含恶意指令 |

## 2. 三种结构模式

### 2.1 分层结构（Hierarchical Prompt）

将 Prompt 分为多个独立层次，每层有明确优先级。高层规则不可被低层覆盖。

**Test-Agent 实践（runtime/router/prompt.py）：**
- 第1层: HARD RULES（硬约束，不可覆盖）
- 第2层: Schema定义（结构化输出格式）
- 第3层: Behavior Rules（行为指导）
- 第4层: Fallbacks（兜底策略）

### 2.2 优先级链（Priority Chain）

多个 Prompt 源按优先级合并：CLI参数 > 环境变量 > 项目配置 > 用户配置 > 系统默认

**Test-Agent 实现：** `runtime/config/settings.py` 5层配置优先级

### 2.3 角色隔离（Role Isolation）

System Prompt 内部划分为不可变角色区，用户输入永远不能跨越到 System 区域：

```
+-- SYSTEM ROLE (不可变) -------+
| 1. Core Rules (HARD RULES)   |
| 2. Task Context (当前任务)    |
| 3. Tool Definitions (工具)   |
+-------------------------------+
     ↓ (单向注入，不可反向)
+-- USER ROLE (隔离) ----------+
| 4. User Input (用户输入)     |
+-------------------------------+
```

## 3. 反漂移机制

### 3.1 周期重注入
每 N 轮对话（建议10-15轮）重新注入核心规则摘要，以 `[REMINDER]` 标记。

### 3.2 验证锚点
在关键决策点前插入强制验证步骤，Agent 必须通过验证才能继续。

### 3.3 上下文预算
设定 Token 预算，接近时触发 compaction：保留 HARD RULES 完整，压缩对话历史。

## 4. 安全护栏（6层纵深防御）

| 层 | 名称 | 作用 |
|----|------|------|
| L1 | 输入隔离 | 用户输入标记 USER 角色，永不 SYSTEM |
| L2 | 输出验证 | LLM 工具调用执行前验证 |
| L3 | 敏感操作确认 | 破坏性操作必须二次确认（TUI弹窗） |
| L4 | 角色隔离 | 核心规则 > 任务 > 上下文 3级不可变 |
| L5 | 输入消毒 | 控制字符、同形字、注入模式检测 |
| L6 | 审计日志 | 记录所有被拦截的注入尝试 |

## 5. 注入检测模式（runtime/agent/prompt_guard.py）

```python
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?)",
    r"(?i)you\s+are\s+(now\s+)?(a\s+)?(different|new)\s+(ai|assistant|agent|role)",
    r"(?i)override\s+(the\s+)?(system|instructions?|rules?|prompt)",
    r"(?i)forget\s+(everything|all\s+you\s+know|your\s+training)",
    r"(?i)disregard\s+(previous|all|any)\s+(instructions?|constraints?|rules?)",
    r"(?i)system\s*:\s*you\s+are",
    r"(?i)act\s+as\s+(if\s+you\s+are|a\s+different)",
]
```

## 6. Test-Agent 的 Prompt 体系

| 组件 | 数量 | 路径 |
|------|------|------|
| 主 Agent System Prompt | 2 | runtime/router/prompt.py, v2_prompt.py |
| 子 Agent 定义 | 16 | ai/agents/01~16-*.md |
| Skill 定义 | 32 | ai/skills/*.md |
| Agent 角色定义 | 16 | ai/agents/ |

## 7. 建议改进

### 短期（Sprint 3-4）
- [ ] 主 Prompt 重构为 5 层分层结构（当前扁平）
- [ ] 统一 16 个 Agent 定义的 Prompt 模板格式
- [ ] 反漂移机制（周期重注入 + 验证锚点）
- [ ] 每个 Skill 增加"前置条件"和"验证检查点"

### 长期（Sprint 5-7）
- [ ] Hook 系统扩展至 10+ 事件类型
- [ ] 用户自定义 Prompt 片段注入（tagent.yml）
- [ ] Prompt 版本化与 A/B 测试框架
- [ ] 多语言 Prompt 模板

## 8. 对标项目 Prompt 模式对比

| 特性 | Claude Code | Codex CLI | Test-Agent（当前）|
|------|------------|-----------|-----------------|
| Prompt 结构 | 分层+角色隔离 | TOML配置 | 单一SYSTEM_PROMPT |
| 工具定义 | 函数签名+描述 | TOML声明式 | JSON Schema |
| 反漂移 | Compaction+摘要 | 工作树隔离 | 无显式机制 |
| 注入防御 | 角色隔离+消毒 | 沙箱分层 | 6层纵深防御 ✅ |
| 权限模型 | 3级 | 3级+审批 | 3级+路径匹配 ✅ |
| Hook系统 | 20+事件 | 配置文件 | 3事件 |

---

*研究完成: 2026-06-21 | 对标: Claude Code + Codex CLI + Gemini CLI*
