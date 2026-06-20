# FIX-LOG — 修复记录

> **最后更新:** 2026-06-20 Sprint 0 Day 1

---

## Sprint 0 修复状态

### 阻塞级（CRITICAL）

| ID | 问题 | 状态 |
|----|------|------|
| F-001 | `slash_handlers.py` 1864行超800行 | ✅ 已修复 — 拆为79行门面+4子文件(max 757行) |
| F-002 | `interactive.py` 1101行超800行 | 🔜 延期 — 38函数共享全局变量，拆分风险>收益 |
| F-003 | `run_decision_direct()` CC=42 | ✅ 已修复 — CC=11, 148→54行, 消除重复代码 |
| F-004 | `execute_node()` CC=28 | ✅ 已修复 — CC=9, 198→33行, 统一Expert/Skill路径 |
| F-005 | `analyze()` CC=26 | ✅ 已修复 — CC=4, 112→37行 |
| F-006 | `parse()` CC=25 | ✅ 已修复 — CC=3, 78→23行, 策略模式 |
| F-007 | `_cmd_task()` CC=24 | ✅ 在slash_handlers_ops.py中, 随P0-001拆分 |
| F-008 | `register()` + `demo()` CC=21 | ✅ 已修复 — CC=4, 4步函数提取 |
| F-009 | `_extract_text_from_payload()` CC=20 | ✅ 已修复 — CC=1, 50→4行, 字典派发表 |
| F-010 | `skills.registry` 导入失败 | ✅ 审计误报 — 代码库中无此导入 |

### 高级（HIGH）

| ID | 问题 | 状态 |
|----|------|------|
| F-011 | `defect_tracker/base.py` 5个`...` | ✅ 审计误报 — `@abc.abstractmethod` 正确Python模式 |
| F-012 | `agents/base.py` 3个空壳 | ✅ 审计误报 — `@abc.abstractmethod` 正确Python模式 |
| F-013 | `exporters/base.py` `export()` | ✅ 审计误报 — `@abc.abstractmethod` 正确Python模式 |
| F-014 | `backends/daytona.py` 2个pass | ✅ 审计误报 — 有注释合法空操作(ambient auth) |
| F-015 | `backends/docker.py` 1个pass | ✅ 审计误报 — 有注释合法空操作(don't auto-rm) |
| F-016 | `backends/local.py` 2个pass | ✅ 审计误报 — 合法空操作(无需连接/清理) |
| F-017 | `backends/singularity.py` 2个pass | ✅ 审计误报 — 合法空操作(无需连接/清理) |

### 中级（MEDIUM/LOW）

| ID | 问题 | 状态 |
|----|------|------|
| F-018 | 15个未使用导入 | ⏳ Sprint 1处理(LOW优先级) |
| F-019 | Discord webhook URL硬编码 | ⏳ Sprint 1处理 |
| F-020 | 42个孤立图谱节点 | ✅ 已验证 — 14个`__init__.py`标记+6个构建配置+3个MD定义+19个文档/资源节点, 0死代码 |

---

## 修复详情

### F-001: slash_handlers.py拆分
- **日期:** 2026-06-20
- **改动前:** 1864行单文件, 58个函数
- **改动后:** 79行门面 + 4子文件: core(293)/config(485)/ops(757)/data(362)
- **验证:** 43测试全绿, 所有import兼容

### F-003: run_decision_direct()分解
- **日期:** 2026-06-20
- **改动前:** CC=42, 148行, 批处理/单处理重复代码
- **改动后:** CC=11, 54行主函数 + 9个子函数(max CC=10)
- **提取:** _classify_result, _mark_unreachable, _find_ready_nodes, _drain_inflight, _process_batch_results, _block_on_oldest, _build_dag_summary

### F-004: execute_node()分解
- **日期:** 2026-06-20
- **改动前:** CC=28, 198行, Expert/Skill路径重复代码
- **改动后:** CC=9, 33行主函数 + 3个子函数
- **提取:** _check_impl_status(22行), _run_runner(34行, 统一Expert/Skill), _run_script_fallback(50行)

### F-005: analyze()分解
- **日期:** 2026-06-20
- **改动前:** CC=26, 112行
- **改动后:** CC=4, 37行主函数 + 7个子函数
- **提取:** _collect_seed_nodes, _add_seed_from_file, _add_seed_by_suffix, _collect_blast_radius, _collect_impacted_tests, _recommendation

### F-006: parse()分解
- **日期:** 2026-06-20
- **改动前:** CC=25, 78行
- **改动后:** CC=3, 23行主函数 + 5个子函数
- **提取:** _parse_at_time, _parse_every_interval, _build_cron_values, _validate_cron, _match_general_pattern

### F-008: demo.py分解
- **日期:** 2026-06-20
- **改动前:** CC=21, ~200行
- **改动后:** CC=4, ~80行 + 6个子函数
- **提取:** _setup_demo_llm, _run_preflight_smoke, _demo_init_step, _demo_doctor_step, _demo_selftest_step, _demo_artifacts_step

### F-009: _extract_text_from_payload()重构
- **日期:** 2026-06-20
- **改动前:** CC=20, 50行if-elif链
- **改动后:** CC=1, 4行 + 5个平台函数 + _EXTRACTORS字典
- **提取:** _extract_telegram/discord/feishu/dingtalk/qqbot

### F-020: 孤立图谱节点验证
- **日期:** 2026-06-20
- **发现:** 42个节点中: 14个`__init__.py`标记, 6个构建配置, 3个MD Agent定义, 19个文档/资源节点
- **结论:** 0死代码, 全部为基础设施标记或文档资源
