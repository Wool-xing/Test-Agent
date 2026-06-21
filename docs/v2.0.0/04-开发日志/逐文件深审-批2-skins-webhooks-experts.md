# §三-C 逐文件深审 — 批2: skins + webhooks + experts

> 日期: 2026-06-21
> 审查Agent: code-reviewer × 3 (并行独立审查)
> 文件: skins.py(715行) + webhooks.py(582行) + experts.py(410行)

---

## skins.py (715行) — 0C/0H/3M/3L

| ID | 严重级 | 问题 | 修复 | 状态 |
|----|--------|------|------|------|
| SR-001 | MEDIUM | :707 3个lazy import无异常保护 | try/except + fallback banner | ✅ |
| SR-002 | MEDIUM | :14 660行monolithic dict, 无自定义主题加载 | SkinSchema dataclass + YAML加载 | ⏸️ Sprint 6 |
| SR-003 | MEDIUM | :687 set_skin未持久化, 重启丢失 | 写入profile config | ⏸️ Sprint 2A |

## webhooks.py (582行) — 1C/2H/4M/3L

| ID | 严重级 | 问题 | 修复 | 状态 |
|----|--------|------|------|------|
| WR-001 | CRITICAL | :39 Discord/DingTalk/QQ签名验证 环境变量缺失→返回True绕过 | fail-closed: return False | ✅ |
| WR-002 | HIGH | :38 Discord/QQ未校验timestamp新鲜度, 无防重放 | 5分钟窗口校验 + ImportError fail-closed | ✅ |
| WR-003 | HIGH | :491 _process_async_with_reply未实际回复 | 实现DingTalk/QQ Bot reply API | ⏸️ Sprint 4 |
| WR-004 | MEDIUM | :440 异常exc直接拼入用户回复 | 改为通用错误消息 "详情已记录日志" | ✅ |

## experts.py (410行) — 0C/1H/4M/1L

| ID | 严重级 | 问题 | 修复 | 状态 |
|----|--------|------|------|------|
| ER-001 | HIGH | :312 runner.run()无超时, LLM hang→DAG永久阻塞 | TODO标注 + TD-015 backlog | ✅ |
| ER-002 | MEDIUM | :268 script kind绕过_impl_status门禁 | kind in ("expert","skill","script") | ✅ |
| ER-003 | MEDIUM | :34 EXPERT_SCRIPT_MAP硬编码重复catalog | 从catalog推导 | ⏸️ Sprint 5 |

---

## 可执行行动清单 (需立即修复的⬜项)

| ID | 严重级 | 文件 | 行动 | 状态 |
|----|--------|------|------|------|
| B2-001 | HIGH | webhooks.py | WR-002: 加timestamp 5分钟新鲜度校验 | ✅ |
| B2-002 | HIGH | webhooks.py | WR-003: _process_async_with_reply实现回复 | ⏸️ Sprint 4 |
| B2-003 | MEDIUM | webhooks.py | WR-004: exc脱敏 | ✅ |
| B2-004 | MEDIUM | skins.py | SR-001: lazy import try/except | ✅ |
| B2-005 | MEDIUM | experts.py | ER-002: script kind门禁 | ✅ |

## 汇总

| 文件 | CRITICAL | HIGH | MEDIUM | LOW |
|------|----------|------|--------|-----|
| skins.py | 0 | 0 | 3 | 3 |
| webhooks.py | 1→0 | 2 | 4 | 3 |
| experts.py | 0 | 1→0 | 4 | 1 |
| **合计** | **0** | **2** | **11** | **7** |

---
*审查完成: 2026-06-21 | §三-C 累计: 5/364文件*
