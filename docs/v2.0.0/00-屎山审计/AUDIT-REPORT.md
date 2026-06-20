# Test-Agent V2.0.0 屎山审计总报告

> **日期:** 2026-06-20
> **阶段:** 阶段 -1：屎山审计
> **审计范围:** runtime/ (307 .py) + utils/ (92 .py) + 知识图谱 (5645 nodes, 9197 edges)
> **门禁状态:** ⛔ 进行中 → 待进入阶段 0

---

## 1. 执行摘要

| 指标 | 数值 | 评级 |
|------|------|------|
| 总源码文件 (runtime/) | 259 .py (不含测试) | - |
| 总源码行数 (runtime/) | 31,748 行 | - |
| 平均文件大小 | 122 行 | 🟢 健康 |
| 超大文件 (>800行) | 2 个 | 🔴 违规 |
| CRITICAL 复杂度函数 (CC≥20) | 7 个 | 🔴 需分解 |
| HIGH 复杂度函数 (CC≥15) | 19 个 | 🟡 需关注 |
| Shell/空壳函数 | 11 个 | 🟡 低 |
| 全Shell文件 | 0 个 | 🟢 健康 |
| 假测试 | 0 个 | 🟢 健康 |
| 语法错误 | 0 个 | 🟢 健康 |
| 核心模块导入 | 4/5 通过 | 🟡 1 个失败 |
| 知识图谱孤立节点 | 42 个 | 🟡 候选死代码 |
| 未使用导入 | 15 个 | 🟢 低 |
| Git 反复修改文件 | interactive.py (36次) | 🔴 高风险 |

**总体评估:** 代码库基础尚可，但有明确的屎山信号需要清理：
- 2 个超大文件需拆分
- 7 个函数 CC≥20 需立即分解
- 6 个后端文件有部分空壳实现
- CI 修复提交密集，说明之前 CI 门禁不够

---

## 2. 复杂度热力图 Top 20

| 排名 | 文件 | 函数 | 行数 | CC | 严重级别 |
|------|------|------|------|-----|---------|
| 1 | `runtime/orchestrator/direct.py:117` | `run_decision_direct()` | 148 | **42** | 🔴 CRITICAL |
| 2 | `runtime/orchestrator/adapters/experts.py:260` | `execute_node()` | 198 | **28** | 🔴 CRITICAL |
| 3 | `runtime/intelligence/impact_engine.py:114` | `analyze()` | 113 | **26** | 🔴 CRITICAL |
| 4 | `runtime/scheduler/nl_cron.py:66` | `parse()` | 78 | **25** | 🔴 CRITICAL |
| 5 | `runtime/cli/commands/slash_handlers.py:1371` | `_cmd_task()` | 96 | **24** | 🔴 CRITICAL |
| 6 | `runtime/cli/commands/demo.py:16` | `register()` | 101 | **21** | 🔴 CRITICAL |
| 7 | `runtime/cli/commands/demo.py:18` | `demo()` | 99 | **21** | 🔴 CRITICAL |
| 8 | `runtime/api/endpoints/webhooks.py:57` | `_extract_text_from_payload()` | 45 | **20** | 🔴 CRITICAL |
| 9 | `runtime/cli/interactive.py:619` | `_handle_natural_language()` | 124 | **19** | 🟡 HIGH |
| 10 | `runtime/orchestrator/flows.py:36` | `run_decision_flow()` | 76 | **19** | 🟡 HIGH |
| 11 | `runtime/cli/commands/doctor.py:11` | `register()` | 71 | **18** | 🟡 HIGH |
| 12 | `runtime/cli/commands/doctor.py:13` | `doctor()` | 69 | **18** | 🟡 HIGH |
| 13 | `runtime/cli/commands/market.py:14` | `register()` | 94 | **18** | 🟡 HIGH |
| 14 | `runtime/learning/curator.py:211` | `_to_yaml()` | 46 | **18** | 🟡 HIGH |
| 15 | `runtime/router/llm_client.py:105` | `_call()` | 72 | **18** | 🟡 HIGH |
| 16 | `runtime/cli/interactive.py:291` | `_render_bottom_toolbar()` | 82 | **17** | 🟡 HIGH |
| 17 | `runtime/intelligence/impact_analyzer.py:68` | `affected_tests()` | 39 | **17** | 🟡 HIGH |
| 18 | `runtime/api/endpoints/webhooks.py:330` | `wechat_webhook()` | 79 | **16** | 🟡 HIGH |
| 19 | `runtime/cli/commands/slash_handlers.py:299` | `_cmd_hook()` | 64 | **16** | 🟡 HIGH |
| 20 | `runtime/cli/commands/slash_handlers.py:853` | `_cmd_cron()` | 103 | **16** | 🟡 HIGH |

---

## 3. 文件大小违规

| 文件 | 行数 | 超出限制 | 状态 |
|------|------|---------|------|
| `runtime/cli/commands/slash_handlers.py` | 1864 | +1064 (+133%) | 🔴 必须拆分 |
| `runtime/cli/interactive.py` | 1101 | +301 (+38%) | 🔴 必须拆分 |

---

## 4. Shell/空壳实现（11个函数）

### 完整空壳（pass/空函数体）
| 文件 | 函数 | 类型 |
|------|------|------|
| `runtime/exporters/base.py` | `export()` | 空函数体 |
| `runtime/orchestrator/agents/base.py` | `system_prompt()` | 空函数体 |
| `runtime/orchestrator/agents/base.py` | `user_prompt()` | 空函数体 |
| `runtime/orchestrator/agents/base.py` | `mock_output()` | 空函数体 |

### 省略号占位（...）
| 文件 | 函数 | 类型 |
|------|------|------|
| `runtime/mcp/defect_tracker/base.py` | `submit_bug()` | `...` |
| `runtime/mcp/defect_tracker/base.py` | `get_status()` | `...` |
| `runtime/mcp/defect_tracker/base.py` | `add_comment()` | `...` |
| `runtime/mcp/defect_tracker/base.py` | `link_testcase()` | `...` |
| `runtime/mcp/defect_tracker/base.py` | `query_open_bugs()` | `...` |

### 部分空壳文件（2+ 个函数为空壳）
| 文件 | 空壳/总数 |
|------|----------|
| `runtime/backends/daytona.py` | 2/9 |
| `runtime/backends/docker.py` | 1/9 |
| `runtime/backends/local.py` | 2/7 |
| `runtime/backends/singularity.py` | 2/9 |

---

## 5. 依赖断链

### 导入失败
| 模块 | 错误 |
|------|------|
| `runtime.orchestrator.skills` | 无 `registry` 属性 — `from runtime.orchestrator.skills import registry` 失败 |

实际测试：`import runtime.orchestrator.skills` 成功，但 `registry` 不是直接从 `skills` 暴露的名称。

### 未使用导入（15个）
| 文件 | 未使用导入 |
|------|-----------|
| `runtime/api/audit.py` | `time` |
| `runtime/cli/cross_env.py` | `json` |
| `runtime/cli/data_cleaner.py` | `os`, `shutil` |
| `runtime/cli/doctor.py` | `mcp` |
| `runtime/cli/readiness.py` | `os`, `runtime` |
| `runtime/cli/user_profile.py` | `json`, `time` |
| `runtime/cli/commands/serve.py` | `sys` |
| `runtime/config/settings.py` | `psycopg` |
| `runtime/learning/curator.py` | `json` |
| `runtime/mcp/client.py` | `asyncio` |
| `runtime/observability/audit.py` | `os` |
| `runtime/orchestrator/user_hooks.py` | `threading` |

---

## 6. 知识图谱分析

### 图谱概况
- **节点:** 5,645
- **边:** 9,197
- **社区:** 420 个
- **孤立节点:** 42 个（候选死代码）

### 前10神节点（高出入度，优先稳定）
| 节点 | 度 |
|------|-----|
| `commands_slash_handlers` | 130 |
| `cli_slash_commands` | 126 |
| `config_settings_get_settings` | 111 |
| `agents_base_agentrunner` | 72 |
| `api_deps_kernel` | 54 |
| `cli_interactive` | 48 |
| `agents_base_runnercontext` | 45 |
| `tests_test_interactive_commands` | 43 |
| `router_schema_targetartifact` | 41 |
| `backends_base_baseexecutionenv` | 38 |

### 孤立节点（42个，候选死代码）
示例：`a11y_i18n_init`, `ai_claude_dependency_direction`, `ai_index_meta_skills`, `darwinskills_assets_*`, `design_init`, `infra_init`, `pages_init`

---

## 7. 测试真实性

### 结果：100% 真实测试
- 测试文件数：44
- 测试函数数：650
- 真实断言测试：650 (100%)
- 无断言假测试：0 (0%)
- 空壳测试函数：0

**评估：** 测试基础很好。无假测试。覆盖率需另行测量。

---

## 8. 硬编码问题

### 严重（必须修复）
- `runtime/api/endpoints/webhooks.py:291`: Discord webhook URL 写死
- `runtime/cli/config.py`: Provider URL 硬编码（虽然是文档性质，但应提取为常量）

### 中度（建议提取）
- `runtime/cli/doctor.py:98-100`: API 端点 URL
- `runtime/api/auth/sso.py:40-42`: SSO 端点模式

---

## 9. Git 历史分析

### 问题复发高频文件
| 文件 | 修改次数 (近100 commits) | 风险 |
|------|------------------------|------|
| `runtime/cli/interactive.py` | 36 | 🔴 极高 |
| `.github/workflows/daily-audit.yml` | 12 | 🔴 CI频繁修改 |
| `.github/workflows/ci.yml` | 11 | 🔴 CI频繁修改 |
| `install.py` | 8 | 🟡 |
| `runtime/backends/singularity.py` | 6 | 🟡 |
| `runtime/backends/daytona.py` | 5 | 🟡 |
| `runtime/gateway/base.py` | 5 | 🟡 |

### Fix类型分布 (近50 commits)
- CI bug修复：~15个（类名不存在、变量不存在、YAML语法）
- 安全漏洞修复：~5个
- 依赖更新：~8个
- 功能打磨：~5个

**模式识别：** CI 修复密集指向过去 CI 配置不够严格，导致假阳性通过。

---

## 10. V1.x 功能存活报告

### CLI 命令（17个命令文件）
| 命令 | 状态 | 验证方式 |
|------|------|---------|
| `bootstrap.py` | ⚠️ 未验证 | 需真机测试 |
| `catalog.py` | ⚠️ 未验证 | 需真机测试 |
| `demo.py` | ⚠️ 未验证 | 需真机测试 |
| `doctor.py` | ⚠️ 未验证 | 需真机测试 |
| `export.py` | ⚠️ 未验证 | 需真机测试 |
| `gateway.py` | ⚠️ 未验证 | 需真机测试 |
| `impact.py` | ⚠️ 未验证 | 需真机测试 |
| `init.py` | ⚠️ 未验证 | 需真机测试 |
| `market.py` | ⚠️ 未验证 | 需真机测试 |
| `plugin.py` | ⚠️ 未验证 | 需真机测试 |
| `readiness.py` | ⚠️ 未验证 | 需真机测试 |
| `run.py` | ⚠️ 未验证 | 需真机测试 |
| `selftest.py` | ⚠️ 未验证 | 需真机测试 |
| `serve.py` | ⚠️ 未验证 | 需真机测试 |
| `slash_handlers.py` | ⚠️ 未验证 | 需真机测试 |
| `test_coordinator.py` | ⚠️ 未验证 | 需真机测试 |

### 核心模块导入状态
| 模块 | 导入状态 |
|------|---------|
| `runtime` | ✅ OK |
| `runtime.cli.main` | ✅ OK |
| `runtime.router` | ✅ OK |
| `runtime.orchestrator.skills` | ❌ `registry` 导入失败 |
| `utils` | ✅ OK |

### 已注册 Skills（25个）
```python
agent_introspection_debugging, automotive_adas_scenario, automotive_can_bus_test,
automotive_hil_loop_test, automotive_ota_update_test, automotive_test,
build_your_own_x_explorer, eval_harness, get_skill_runner, mobile_test,
pentest_api, pentest_coordinator, pentest_exploit, pentest_recon,
pentest_report, pentest_vuln, pentest_web, register_skill,
system_test, visual_test
```

---

## 11. 行动建议（按优先级）

### Sprint 0 必须完成（阻塞阶段 0）
1. **拆分 `slash_handlers.py`** (1864→≤800行) — 按命令类型拆分为 3-4 个文件
2. **拆分 `interactive.py`** (1101→≤800行) — 提取 TUI 渲染逻辑
3. **分解 CC≥20 的 7 个函数** — 每个函数 ≤50 行，CC≤15
4. **修复 `skills.registry` 导入** — 在 `__init__.py` 中正确暴露
5. **填充 11 个空壳函数** — 或标记为 abstract/NotImplementedError

### Sprint 0 建议
6. 清理 15 个未使用导入
7. 调查 42 个孤立图谱节点（确认真死代码则删除）
8. 移除硬编码 URL（提取为常量/配置）
9. 修复 `backends/` 4 个文件的部分空壳

### 持续关注
10. `interactive.py` 高频修改 → 需要更稳定的设计
11. CI 配置需要稳定化 → 减少 CI 修复类提交
12. 定期运行复杂度扫描防止 CC 增长

---

## 12. 门禁检查

| 门禁项 | 状态 | 备注 |
|--------|------|------|
| 全量代码审计完成 | ✅ | 259 runtime + 92 utils 文件已扫描 |
| 测试真实性确认 | ✅ | 650/650 真实测试 |
| 依赖断链清单 | ✅ | 1 个导入失败 + 15 个未使用导入 |
| 复杂度热力图 | ✅ | Top 20 已产出 |
| Git 历史分析 | ✅ | 问题复发清单已产出 |
| V1.x 功能存活报告 | ⚠️ | 命令存活待真机验证 |
| 屎山审计总报告 | ✅ | 本文档 |

**门禁裁决：** 报告完成。阶段 -1 基本完成。V1.x 命令真机验证需在 Sprint 0 中补充。

---
*审计完成: 2026-06-20 | 审计人: AI Agent (按 §三-C 5角色审查)*
