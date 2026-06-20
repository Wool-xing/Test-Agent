# §三-C 逐文件深审 — 高风险TOP3文件

> 日期: 2026-06-21
> 协议: §三-C 每个文件至少3角色审查
> 审查Agent: code-reviewer (安全/测试/架构 + 安全/数据流/产品)
> 文件: interactive.py (787行) + slash_handlers_ops.py (800行)

---

## 文件1: runtime/cli/interactive.py (787行)

### 安全审计专家
- [MEDIUM] :557 — `_handle_slash` 异常路径未对错误消息做凭据脱敏。`_handle_natural_language`(:472-476)有正则清洗, 但`:557`直接输出 `str(_exc)[:200]`→凭据可写入TUI transcript

### 测试专家
- [MEDIUM] :363-370, :402-403, :710-711, :717-719 — 六处 `except Exception: pass` 静默吞错。auto-learn/voice/regression/flaky/discover_plugins/start_background失败均无日志
- [MEDIUM] :91-161 — `_read_multiline`+`_fallback_multiline`(70行)死代码。tui_app.py:54强制multiline=False

### 架构师
- [MEDIUM] :51, :176-180 — 模块级全局可变状态被5个外部模块直接import, 无封装边界
- [MEDIUM] :406-491 — `_handle_natural_language`(85行)混合输入预处理+命令匹配+上下文构建+LLM路由+DAG执行+进度渲染+结果汇总+post-hooks+regression+错误处理

**汇总: 0 CRITICAL, 0 HIGH, 5 MEDIUM, 1 LOW**

---

## 文件2: runtime/cli/commands/slash_handlers_ops.py (800行)

### 安全审计专家
- 无CRITICAL/HIGH — 无硬编码token/shell/eval

### 数据流专家
- [HIGH] :773-783 — `/cross env dev run tests` 解析envs为`[]`, 静默回退到`["test","staging"]`
- [MEDIUM] :378-380 — `distill_skill()` 异常时`_last_trace`未重置, 泄漏到下次`/distill`调用
- [MEDIUM] :664-720 — task状态无转换守卫, done→cancelled无验证

### 产品设计专家
- [HIGH] :782-783 — /cross解析bug: 用户指定单env被忽略
- [MEDIUM] :430-431 — `_cmd_api` unknown action不显示用户输入
- [LOW] :118, :153, :178 — 不一致前缀 (!cron/!alias vs /search)

**汇总: 0 CRITICAL, 2 HIGH, 4 MEDIUM, 4 LOW**

---

## 可执行行动清单

| ID | 严重级 | 文件:行 | 问题 | 修复 | 状态 |
|----|--------|--------|------|------|------|
| DR-001 | HIGH | slash_handlers_ops.py:773 | /cross单env被忽略 | 修复env解析: len(sub)≥2判断 | ✅ |
| DR-002 | HIGH | slash_handlers_ops.py:782 | /cross静默回退 | 加yellow warning | ✅ |
| DR-003 | MEDIUM | interactive.py:557 | 凭据可能泄漏到transcript | 共用脱敏函数 | ⬜ |
| DR-004 | MEDIUM | interactive.py:363+ | 6处静默吞错 | 加logger.warning | ⬜ |
| DR-005 | MEDIUM | interactive.py:91 | multiline死代码(70行) | 标注legacy或移除 | ⬜ |
| DR-006 | MEDIUM | interactive.py:51 | 全局可变状态耦合 | 收敛到Context对象 | ⬜ |
| DR-007 | MEDIUM | slash_handlers_ops.py:378 | _last_trace状态泄漏 | try/finally包裹 | ✅ |
| DR-008 | MEDIUM | slash_handlers_ops.py:664 | task状态无转换守卫 | 加状态机验证 | ⬜ |

---

*审查完成: 2026-06-21 | 下一批: skins.py + webhooks.py + experts.py*
