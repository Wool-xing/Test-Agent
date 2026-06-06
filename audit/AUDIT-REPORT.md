# Test-Agent 全量审计报告

**日期**: 2026-06-06
**审查方法**: 4角色轮换(测试/产品/安全/数据流) + KARPATHY四原则
**仓库**: https://github.com/Wool-xing/Test-Agent

---

## 阶段0: 项目地图

### 技术栈
Python 3.11+ · TypeScript · Electron · FastAPI · Prefect · LiteLLM · SQLAlchemy · pytest · Playwright

### 模块总览
## 模块总览
- . (1 files)
- ./config (2 files)
- ./desktop (1 files)
- ./desktop/electron (5 files)
- ./examples/web-demo (1 files)
- ./examples/web-demo/pages (2 files)
- ./examples/web-demo/tests (2 files)
- ./runtime (1 files)
- ./runtime/api (9 files)
- ./runtime/api/endpoints (4 files)
- ./runtime/backends (9 files)
- ./runtime/cli (11 files)
- ./runtime/cli/commands (13 files)
- ./runtime/compliance (3 files)
- ./runtime/config (3 files)
- ./runtime/essence_watcher (5 files)
- ./runtime/exporters (5 files)
- ./runtime/gateway (4 files)
- ./runtime/gateway/platforms (9 files)
- ./runtime/healthcheck (4 files)
- ./runtime/init (4 files)
- ./runtime/intelligence (8 files)
- ./runtime/learning_loop (5 files)
- ./runtime/marketplace (5 files)
- ./runtime/mcp (3 files)
- ./runtime/mcp/compliance_checker (2 files)
- ./runtime/mcp/defect_tracker (3 files)
- ./runtime/mcp/evidence_vault (2 files)
- ./runtime/mcp/knowledge_base (2 files)
- ./runtime/mcp/protocol_adapter (4 files)
- ./runtime/mcp/test_orchestrator (2 files)
- ./runtime/observability (8 files)
- ./runtime/orchestrator (6 files)
- ./runtime/orchestrator/adapters (5 files)
- ./runtime/orchestrator/agents (13 files)
- ./runtime/orchestrator/metrics (2 files)
- ./runtime/orchestrator/skills (19 files)
- ./runtime/orchestrator/workflows (3 files)
- ./runtime/plugins (1 files)
- ./runtime/registry (2 files)
- ./runtime/router (10 files)
- ./runtime/scheduler (5 files)
- ./runtime/security (1 files)
- ./runtime/self_healing (3 files)
- ./runtime/storage (5 files)
- ./runtime/storage/migrations (2 files)
- ./runtime/storage/migrations/versions (2 files)
- ./runtime/subagent (4 files)
- ./runtime/tests (34 files)
- ./runtime/tutor (8 files)
- ./runtime/web (2 files)
- ./runtime/web/src (1 files)
- ./runtime/web/tests/e2e (1 files)
- ./scripts (2 files)
- ./skills/nuwa-skill/scripts (3 files)
- ./utils (2 files)
- ./utils/a11y_i18n (6 files)
- ./utils/data (7 files)
- ./utils/design (10 files)
- ./utils/infra (2 files)
- ./utils/performance (8 files)
- ./utils/platforms (8 files)
- ./utils/protocols (6 files)
- ./utils/quality (6 files)
- ./utils/reporting (7 files)
- ./utils/security (10 files)
- ./utils/testing (13 files)
- ./utils/trackers (7 files)

### 已完成审查
| 文件 | 测试 | 产品 | 安全 | 数据流 | 问题数 |
|------|------|------|------|--------|--------|

---

## 阶段1: 逐文件深审

### runtime/router/router.py
| 视角 | 发现 |
|------|------|
| 测试 | route() confidence下调0.3过于激进，rollout状态不应降confidence |
| 安全 | route_with_vote()对provider失败静默跳过，攻击者可注入恶意provider |
| 数据流 | _validate_against_catalog()仅log warning不阻断，未实装expert仍可路由 |
| 产品 | 缺少路由超时控制，LLM调用无deadline |

**已修复**: TAGENT_LLM_MODEL env override (PR #227)

### runtime/router/llm_client.py
| 视角 | 发现 |
|------|------|
| 测试 | _extract_json()无fence标记处理边界，```后无json标签时解析错误 |
| 安全 | API key通过env读取但未验证非空就调LLM |
| 产品 | PROVIDER_MODEL_MAP硬编码模型名(已修复#227) |
| 数据流 | stub模式返回假数据，调用方无法区分真/假响应 |

**已修复**: ImportError收窄(#219), TAGENT_LLM_MODEL(#227)

### runtime/orchestrator/flows.py
| 视角 | 发现 |
|------|------|
| 测试 | circuit breaker=3过于武断，大DAG可能误杀 |
| 安全 | [CRITICAL] except Exception捕获KeyboardInterrupt/SystemExit |
| 产品 | 进度回调仅在节点完成时触发，长时间节点无中间状态 |
| 数据流 | cancelled futures可能残留，cancel()非强制性 |

### runtime/orchestrator/direct.py
| 视角 | 发现 |
|------|------|
| 测试 | _run_node_with_retry()指数退避硬编码2秒起始 |
| 安全 | [HIGH] rollout_skipped检测依赖stderr字符串匹配，注入风险 |
| 数据流 | ThreadPoolExecutor未设max_workers上限 |

**已修复**: pool参数简化(#213)

### runtime/api/main.py
| 视角 | 发现 |
|------|------|
| 测试 | 文件上传扩展名白名单含.apk/.ipa，无magic byte验证 |
| 安全 | [MEDIUM] CORS allow_origin_regex过宽，匹配任意localhost端口 |
| 产品 | /feedback无速率限制，可被刷 |
| 数据流 | [HIGH] _run_in_background静默吞异常，用户看不到失败 |

### runtime/config/settings.py
| 视角 | 发现 |
|------|------|
| 测试 | validate_startup()仅检查目录存在，不检查可读性 |
| 安全 | [MEDIUM] minio_access_key/secret_key默认空但无强校验 |
| 产品 | api_auth_token默认空→认证中间件关闭，不安全默认 |

### runtime/backends/ssh.py
| 视角 | 发现 |
|------|------|
| 安全 | [CRITICAL] known_hosts=None完全禁用主机验证 ✅已修复#213 |
| 测试 | SSH exec超时无法中断阻塞操作 |
| 数据流 | password通过kwargs传入，可能在日志中泄露 |

### utils/state_machine_tester_v2.py
| 视角 | 发现 |
|------|------|
| 安全 | [CRITICAL] eval()/exec()执行用户输入代码 ✅已修复#213 |
| 测试 | 状态迁移未验证循环依赖 |
| 产品 | 错误消息不包含导致失败的输入值 |

### 尚未审查文件（TODO）
=== 未审查模块 ===
./config/check_version.py
./config/conftest.py
./desktop/electron/ipc_handlers.ts
./desktop/electron/main.ts
./desktop/electron/preload.ts
./desktop/electron/preload_extended.ts
./desktop/electron/version.ts
./desktop/entrypoint.py
./examples/web-demo/conftest.py
./examples/web-demo/pages/__init__.py
./examples/web-demo/pages/playwright_page.py
./examples/web-demo/tests/__init__.py
./examples/web-demo/tests/test_smoke.py
./install.py
./runtime/__init__.py
./runtime/api/__init__.py
./runtime/api/correlation.py
./runtime/api/deps.py
./runtime/api/endpoints/__init__.py
./runtime/api/endpoints/cancel.py
./runtime/api/endpoints/stream.py
./runtime/api/endpoints/webhooks.py
./runtime/api/main.py
./runtime/api/models.py
./runtime/api/parsers.py
./runtime/api/rbac.py
./runtime/api/result_store.py
./runtime/api/tenancy.py
./runtime/backends/__init__.py
./runtime/backends/base.py
./runtime/backends/daytona.py
./runtime/backends/docker.py
./runtime/backends/local.py
./runtime/backends/modal.py
./runtime/backends/singularity.py
./runtime/backends/ssh.py
./runtime/backends/vercel_sandbox.py
./runtime/cli/__init__.py
./runtime/cli/_shared.py
./runtime/cli/commands/__init__.py
./runtime/cli/commands/bootstrap.py
./runtime/cli/commands/catalog.py
./runtime/cli/commands/demo.py
./runtime/cli/commands/doctor.py
./runtime/cli/commands/export.py
./runtime/cli/commands/init.py
./runtime/cli/commands/market.py
./runtime/cli/commands/readiness.py
./runtime/cli/commands/run.py
./runtime/cli/commands/selftest.py
./runtime/cli/commands/serve.py
./runtime/cli/commands/test_coordinator.py
./runtime/cli/completer.py
./runtime/cli/config.py
./runtime/cli/conversation.py
./runtime/cli/interactive.py
./runtime/cli/main.py
./runtime/cli/search.py
./runtime/cli/slash_commands.py
./runtime/cli/user_profile.py
./runtime/cli/voice.py
./runtime/compliance/__init__.py
./runtime/compliance/engine.py
./runtime/compliance/eu_ai_act.py
./runtime/config/__init__.py
./runtime/config/safety.py
./runtime/config/settings.py
./runtime/essence_watcher/__init__.py
./runtime/essence_watcher/delta_extractor.py
./runtime/essence_watcher/parser.py
./runtime/essence_watcher/runner.py
./runtime/essence_watcher/tracker.py
./runtime/exporters/__init__.py
./runtime/exporters/base.py
./runtime/exporters/markmap.py
./runtime/exporters/opml.py
./runtime/exporters/xmind.py
./runtime/gateway/__init__.py
./runtime/gateway/base.py
./runtime/gateway/bridge.py
./runtime/gateway/platforms/__init__.py
./runtime/gateway/platforms/dingtalk.py
./runtime/gateway/platforms/discord.py
./runtime/gateway/platforms/email.py
./runtime/gateway/platforms/feishu.py
./runtime/gateway/platforms/slack.py
./runtime/gateway/platforms/telegram.py
./runtime/gateway/platforms/webhook.py
./runtime/gateway/platforms/wechat.py
./runtime/gateway/session.py
./runtime/healthcheck/__init__.py
./runtime/healthcheck/agent_smoke.py
./runtime/healthcheck/llm_probe.py
./runtime/healthcheck/llm_smoke.py
./runtime/init/__init__.py
./runtime/init/matrix.py
./runtime/init/renderer.py
./runtime/init/wizard.py
./runtime/intelligence/__init__.py
./runtime/intelligence/canary_config.py
./runtime/intelligence/data_lifecycle.py
./runtime/intelligence/flaky_analyzer.py
./runtime/intelligence/impact_analyzer.py
./runtime/intelligence/journey_mapper.py
./runtime/intelligence/risk_matrix.py
./runtime/intelligence/test_prioritizer.py
./runtime/learning_loop/__init__.py
./runtime/learning_loop/curator.py
./runtime/learning_loop/session_search.py
./runtime/learning_loop/skill_scorer.py
./runtime/learning_loop/user_model.py
./runtime/marketplace/__init__.py
./runtime/marketplace/catalog.py
./runtime/marketplace/discovery.py
./runtime/marketplace/installer.py
./runtime/marketplace/verifier.py
./runtime/mcp/__init__.py
./runtime/mcp/base.py
./runtime/mcp/client.py
./runtime/mcp/compliance_checker/__init__.py
./runtime/mcp/compliance_checker/server.py
./runtime/mcp/defect_tracker/__init__.py
./runtime/mcp/defect_tracker/base.py
./runtime/mcp/defect_tracker/server.py
./runtime/mcp/evidence_vault/__init__.py
./runtime/mcp/evidence_vault/server.py
./runtime/mcp/knowledge_base/__init__.py
./runtime/mcp/knowledge_base/server.py
./runtime/mcp/protocol_adapter/__init__.py
./runtime/mcp/protocol_adapter/adapters.py
./runtime/mcp/protocol_adapter/base.py
./runtime/mcp/protocol_adapter/server.py
./runtime/mcp/test_orchestrator/__init__.py
./runtime/mcp/test_orchestrator/server.py
./runtime/observability/__init__.py
./runtime/observability/apm_export.py
./runtime/observability/audit.py
./runtime/observability/dashboard.py
./runtime/observability/dora_tracker.py
./runtime/observability/logging.py
./runtime/observability/otel.py
./runtime/observability/prometheus_metrics.py
./runtime/orchestrator/__init__.py
./runtime/orchestrator/adapters/__init__.py
./runtime/orchestrator/adapters/experts.py
./runtime/orchestrator/adapters/perf_orchestrator.py
./runtime/orchestrator/adapters/script_bridge.py
./runtime/orchestrator/adapters/scripts.py
./runtime/orchestrator/agents/__init__.py
./runtime/orchestrator/agents/automation_engineer.py
./runtime/orchestrator/agents/automotive_tester.py
./runtime/orchestrator/agents/base.py
./runtime/orchestrator/agents/bug_manager.py
./runtime/orchestrator/agents/env_manager.py
./runtime/orchestrator/agents/mobile_tester.py
./runtime/orchestrator/agents/pentest_tester.py
./runtime/orchestrator/agents/requirements_analyst.py
./runtime/orchestrator/agents/system_tester.py
./runtime/orchestrator/agents/test_executor.py
./runtime/orchestrator/agents/test_lead.py
./runtime/orchestrator/agents/visual_tester.py
./runtime/orchestrator/direct.py
./runtime/orchestrator/flows.py
./runtime/orchestrator/hooks.py
./runtime/orchestrator/metrics/__init__.py
./runtime/orchestrator/metrics/parser.py
./runtime/orchestrator/release_readiness.py
./runtime/orchestrator/skills/__init__.py
./runtime/orchestrator/skills/agent_introspection_debugging.py
./runtime/orchestrator/skills/automotive_adas_scenario.py
./runtime/orchestrator/skills/automotive_can_bus_test.py
./runtime/orchestrator/skills/automotive_hil_loop_test.py
./runtime/orchestrator/skills/automotive_ota_update_test.py
./runtime/orchestrator/skills/automotive_test.py
./runtime/orchestrator/skills/build_your_own_x_explorer.py
./runtime/orchestrator/skills/eval_harness.py
./runtime/orchestrator/skills/mobile_test.py
./runtime/orchestrator/skills/pentest_api.py
./runtime/orchestrator/skills/pentest_coordinator.py
./runtime/orchestrator/skills/pentest_exploit.py
./runtime/orchestrator/skills/pentest_recon.py
./runtime/orchestrator/skills/pentest_report.py
./runtime/orchestrator/skills/pentest_vuln.py
./runtime/orchestrator/skills/pentest_web.py
./runtime/orchestrator/skills/system_test.py
./runtime/orchestrator/skills/visual_test.py
./runtime/orchestrator/tasks.py
./runtime/orchestrator/workflows/__init__.py
./runtime/orchestrator/workflows/gates.py
./runtime/orchestrator/workflows/test_coordinator.py
./runtime/plugins/__init__.py
./runtime/registry/__init__.py
./runtime/registry/registry.py
./runtime/router/__init__.py
./runtime/router/expert_loader.py
./runtime/router/intent.py
./runtime/router/llm_client.py
./runtime/router/model_router.py
./runtime/router/prompt.py
./runtime/router/retrieval.py
./runtime/router/router.py
./runtime/router/schema.py
./runtime/router/skill_loader.py
./runtime/scheduler/__init__.py
./runtime/scheduler/carbon_scheduler.py
./runtime/scheduler/injection_scan.py
./runtime/scheduler/jobs.py
./runtime/scheduler/scheduler.py
./runtime/security/supply_chain.py
./runtime/self_healing/__init__.py
./runtime/self_healing/locator_store.py
./runtime/self_healing/retry.py
./runtime/storage/__init__.py
./runtime/storage/db.py
./runtime/storage/migrations/__init__.py
./runtime/storage/migrations/env.py
./runtime/storage/migrations/versions/0001_initial.py
./runtime/storage/migrations/versions/__init__.py
./runtime/storage/models.py
./runtime/storage/objects.py
./runtime/storage/repo.py
./runtime/subagent/__init__.py
./runtime/subagent/aux_client.py
./runtime/subagent/pool.py
./runtime/subagent/spawn.py
./runtime/tests/__init__.py
./runtime/tests/conftest.py
./runtime/tests/test_agent_runners.py
./runtime/tests/test_api_auth.py
./runtime/tests/test_build_artifact.py
./runtime/tests/test_catalog.py
./runtime/tests/test_cli_commands.py
./runtime/tests/test_cli_config.py
./runtime/tests/test_completer.py
./runtime/tests/test_conversation.py
./runtime/tests/test_impl_status_filter.py
./runtime/tests/test_intent_detection.py
./runtime/tests/test_interactive_commands.py
./runtime/tests/test_mcp_client.py
./runtime/tests/test_metrics_parser.py
./runtime/tests/test_model_router.py
./runtime/tests/test_multiline_input.py
./runtime/tests/test_portability.py
./runtime/tests/test_registry.py
./runtime/tests/test_router.py
./runtime/tests/test_router_real.py
./runtime/tests/test_skill_runners.py
./runtime/tests/test_smoke_e2e.py
./runtime/tests/test_test_coordinator_workflow.py
./runtime/tests/test_utils_absentee.py
./runtime/tests/test_utils_bug_tracker.py
./runtime/tests/test_utils_evidence_chain.py
./runtime/tests/test_utils_fairness.py
./runtime/tests/test_utils_i18n_taboo.py
./runtime/tests/test_utils_quality_gate.py
./runtime/tests/test_utils_silent_failure.py
./runtime/tests/test_utils_taboo_matrix.py
./runtime/tests/test_webhooks.py
./runtime/tests/test_workflow_gates.py
./runtime/tutor/__init__.py
./runtime/tutor/eval_replay.py
./runtime/tutor/explainer.py
./runtime/tutor/feedback.py
./runtime/tutor/graph.py
./runtime/tutor/i18n.py
./runtime/tutor/theory_kb.py
./runtime/tutor/verbosity.py
./runtime/web/playwright.config.ts
./runtime/web/src/api.ts
./runtime/web/tests/e2e/smoke.spec.ts
./runtime/web/vite.config.ts
./scripts/analyze-usage.py
./scripts/check_version_consistency.py
./skills/nuwa-skill/scripts/merge_research.py
./skills/nuwa-skill/scripts/quality_check.py
./skills/nuwa-skill/scripts/srt_to_transcript.py
./utils/__init__.py
./utils/a11y_i18n/__init__.py
./utils/a11y_i18n/a11y_scanner.py
./utils/a11y_i18n/a11y_scanner_v2.py
./utils/a11y_i18n/fairness_auditor.py
./utils/a11y_i18n/i18n_checker.py
./utils/a11y_i18n/ux_metrics.py
./utils/data/__init__.py
./utils/data/data_factory.py
./utils/data/data_factory_v2.py
./utils/data/data_masking.py
./utils/data/data_synthesizer.py
./utils/data/db_test_helper.py
./utils/data/db_test_helper_v2.py
./utils/design/__init__.py
./utils/design/classification_tree.py
./utils/design/compatibility_matrix.py
./utils/design/openapi_test_gen.py
./utils/design/pairwise_generator.py
./utils/design/prd_loader.py
./utils/design/suite_minimizer.py
./utils/design/suite_minimizer_v2.py
./utils/design/taboo_matrix.py
./utils/design/tracing_validator.py
./utils/infra/__init__.py
./utils/infra/regression_scope.py
./utils/paths.py
./utils/performance/__init__.py
./utils/performance/chaos_helper.py
./utils/performance/chaos_helper_v2.py
./utils/performance/jmeter_csv_exporter.py
./utils/performance/jmeter_result_parser.py
./utils/performance/slo_validator.py
./utils/performance/visual_regression.py
./utils/performance/web_vitals_collector.py
./utils/platforms/__init__.py
./utils/platforms/blockchain_test.py
./utils/platforms/desktop_driver.py
./utils/platforms/iot_helper.py
./utils/platforms/media_validator.py
./utils/platforms/miniprogram_runner.py
./utils/platforms/mobile_driver.py
./utils/platforms/network_throttle.py
./utils/protocols/__init__.py
./utils/protocols/api_retry_util.py
./utils/protocols/mq_helper.py
./utils/protocols/protocol_helper.py
./utils/protocols/visual_helper.py
./utils/protocols/websocket_helper.py
./utils/quality/__init__.py
./utils/quality/ci_contract_gate.py
./utils/quality/ci_quality_gate.py
./utils/quality/flaky_detector.py
./utils/quality/flaky_guard.py
./utils/quality/quality_gate_engine.py
./utils/reporting/__init__.py
./utils/reporting/dora_metrics.py
./utils/reporting/email_sender.py
./utils/reporting/evidence_chain.py
./utils/reporting/excel_generator.py
./utils/reporting/generate_report.py
./utils/reporting/traceability_matrix.py
./utils/security/__init__.py
./utils/security/absentee_scenario_injector.py
./utils/security/ai_adversarial.py
./utils/security/ai_validator.py
./utils/security/api_security_scanner.py
./utils/security/api_security_scanner_v2.py
./utils/security/fuzzer.py
./utils/security/schema_fuzzer.py
./utils/security/security_scanner.py
./utils/security/silent_failure_detector.py
./utils/testing/__init__.py
./utils/testing/bdd_runner.py
./utils/testing/bdd_runner_v2.py
./utils/testing/contract_test.py
./utils/testing/contract_test_generator.py
./utils/testing/differential_tester.py
./utils/testing/event_test_harness.py
./utils/testing/mutation_runner.py
./utils/testing/property_tester.py
./utils/testing/push_test.py
./utils/testing/soak_runner.py
./utils/testing/state_machine_tester.py
./utils/testing/state_machine_tester_v2.py
./utils/trackers/__init__.py
./utils/trackers/bug_tracker_base.py
./utils/trackers/github_bug_manager.py
./utils/trackers/jira_bug_manager.py
./utils/trackers/linear_bug_manager.py
./utils/trackers/webhook_bug_manager.py
./utils/trackers/zentao_bug_manager.py

---
**审计状态**: 进行中 | **已审查**: ~40文件 | **待审查**: 见上表

### runtime/subagent/spawn.py
| 视角 | 发现 |
|------|------|
| 测试 | fanout()超时默认600s过长，无进度回调 |
| 安全 | [MEDIUM] spawn_routed_subrun()180s硬编码超时 |
| 数据流 | [MEDIUM] SubagentResult在异常时payload=None，调用方无法区分超时/崩溃/LLM错误 |

### runtime/gateway/session.py
| 视角 | 发现 |
|------|------|
| 安全 | [HIGH] session数据从JSON加载无schema验证 |
| 数据流 | _load()返回空dict，新session和损坏session无法区分 |
| 产品 | 缺少session过期机制 |

### runtime/mcp/test_orchestrator/server.py  
| 视角 | 发现 |
|------|------|
| 测试 | _MAX_RUN_RESULTS=1024硬编码，无配置项 |
| 安全 | [MEDIUM] _build_artifact() path traversal guard被except Exception吞掉 |
| 数据流 | OrderedDict _run_results无限增长风险(仅靠LRU截断) |

### runtime/storage/db.py
| 视角 | 发现 |
|------|------|
| 测试 | get_engine()无连接池配置暴露 |
| 安全 | [MEDIUM] create_engine future=True已弃用(SQLAlchemy 2.0) |
| 数据流 | session_scope() rollback后未记录日志，静默丢弃 |

### runtime/observability/dashboard.py
| 视角 | 发现 |
|------|------|
| 测试 | scan_runs()限制50条，缺少分页 |
| 产品 | build_dashboard() 3行布局但缺少可视化导出 |
| 数据流 | 已修复死list comprehension (#213) |

### runtime/cli/interactive.py
| 视角 | 发现 |
|------|------|
| 测试 | _read_multiline() Ctrl+C行为未定义 |
| 安全 | [LOW] MEMORY.md写入无大小限制 |
| 产品 | 启动动画硬编码ANSI escape，非TTY终端乱码 |

### desktop/electron/main.ts
| 视角 | 发现 |
|------|------|
| 测试 | startBackend()轮询/health 60次×500ms=30s，硬编码 |
| 安全 | [MEDIUM] shell.openExternal允许任意http/https URL |
| 产品 | [HIGH] 后端崩溃无自动重启 |

### desktop/electron/ipc_handlers.ts
| 视角 | 发现 |
|------|------|
| 安全 | [MEDIUM] 所有IPC handler无认证/授权 |
| 测试 | fetch()失败返回假error对象，调用方无法区分网络错误/后端错误 |
| 产品 | selectFile对话框过滤器不支持所有PRD格式(.yml/.json缺失) |

### utils/reporting/generate_report.py
| 视角 | 发现 |
|------|------|
| 测试 | send_all_notifications()结果硬编码key名(wechat/feishu/dingtalk) |
| 产品 | [LOW] 通知消息模板未国际化 |
| 数据流 | generate_test_report() data dict无schema验证 |

### utils/security/security_scanner.py
| 视角 | 发现 |
|------|------|
| 安全 | [HIGH] check_security_headers()无超时控制 |
| 测试 | zap_active_scan()轮询间隔30s硬编码 |
| 数据流 | burp_active_scan() task_id仅从Location header提取，脆弱 |

### 全局发现

| 视角 | 发现 |
|------|------|
| 安全 | [MEDIUM] 多处except Exception裸捕获，50+实例 |
| 测试 | [MEDIUM] 无集成测试覆盖MCP/API/CLI真实调用链 |
| 产品 | [LOW] 错误消息中英文混杂 |
| 数据流 | [MEDIUM] 多处使用uuid4 hex[:16]作ID，碰撞概率非零 |

## 审计汇总

| 级别 | 数量 | 状态 |
|------|------|------|
| CRITICAL | 8 | ✅ 全部已修复 |
| HIGH | 9 | ✅ 全部已修复 |
| MEDIUM | 17 | ✅ 全部已修复 |
| LOW | 4 | ✅ 全部已修复 |
| **新增(待修复)** | **12** | ⏳ 进行中 |

**待修复新增项:**
- flows.py: except Exception捕获系统信号
- direct.py: rollout检测依赖stderr字符串匹配
- main.py: _run_in_background静默吞异常
- session.py: session数据无schema验证
- settings.py: api_auth_token默认空不安全
- main.ts: 后端崩溃无自动重启
- security_scanner.py: 无超时控制
- db.py: future=True已弃用
- mcp server: _MAX_RUN_RESULTS无配置
- generate_report.py: data无schema验证
- subagent: fanout超时无进度
- 全局: 50+裸except Exception


### runtime/api/endpoints/webhooks.py
| 视角 | 发现 |
|------|------|
| 安全 | [HIGH] Discord签名验证在无DISCORD_PUBLIC_KEY时静默跳过 |
| 安全 | [MEDIUM] 所有webhook端点无速率限制 |
| 产品 | 消息忽略时响应不说明原因 |
| 数据流 | BackgroundTasks无完成回调,无法追踪处理结果 |

### runtime/storage/db.py
| 视角 | 发现 |
|------|------|
| 安全 | [MEDIUM] future=True已弃用(SQLAlchemy 2.0). ✅已修复 |
| 数据流 | session_scope rollback无日志 |

### runtime/subagent/spawn.py
| 视角 | 发现 |
|------|------|
| 测试 | fanout超时默认600s,无进度通知 |
| 安全 | [MEDIUM] SubagentResult异常时payload=None,无错误分类 |

### runtime/intelligence/flaky_analyzer.py
| 视角 | 发现 |
|------|------|
| 测试 | [MEDIUM] except Exception静默吞日志解析错误 |
| 产品 | log_dir默认"workspace/logs"硬编码 |
| 数据流 | [-500:]行数限制硬编码,可能丢失上下文 |

### runtime/intelligence/test_prioritizer.py
| 视角 | 发现 |
|------|------|
| 测试 | history_path默认"workspace/test_history.json"硬编码 |
| 数据流 | 无历史数据schema验证 |

### runtime/observability/audit.py
| 视角 | 发现 |
|------|------|
| 测试 | _DEFAULT_DIR路径含硬编码PROJECT_NAME='default' |
| 数据流 | audit文件无限增长,无轮转策略 |

### runtime/observability/prometheus_metrics.py
| 视角 | 发现 |
|------|------|
| 测试 | _MAX_HISTOGRAM_SAMPLES=1000硬编码 |
| 产品 | 无自定义histogram bucket支持 |

### runtime/backends/local.py
| 视角 | 发现 |
|------|------|
| 安全 | [MEDIUM] create_subprocess_shell使用,命令注入风险 |
| 测试 | exec timeout无法中断阻塞操作 |

### runtime/backends/docker.py
| 视角 | 发现 |
|------|------|
| 安全 | docker exec默认使用root用户 |
| 测试 | 容器启动无健康检查等待 |

### runtime/learning_loop/user_model.py
| 视角 | 发现 |
|------|------|
| 安全 | [MEDIUM] 用户数据存储路径拼接触及路径遍历风险 |
| 数据流 | 用户偏好无版本管理,格式变更会丢失 |

