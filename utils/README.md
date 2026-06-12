# utils（utils/）索引

73 个 Python 工具模块（含 `__init__.py`），按职责多分类（核心 / 平台 / 协议 / 非功能 / 用例方法 / 测试类型 / 安全增强 / DB/契约/API / 移动专项 / a11y/i18n / 度量 / 区块链/AI 对抗 / 输入）。

> 顶层导航见根目录 `00-项目导航.md`。
> import 路径权威：`from utils.<module> import ...`（部署后 utils/ 在项目根，conftest.py 已注入 sys.path）。

---

## 类别 1：核心通用工具（11 个）— 流程闭环必备

| utils 文件 | 用途 | 关键 API |
|----------|------|---------|
| `api_retry_util.py` | 指数退避重试 10/20/40s | `call_with_retry(func, ...)` / `api_call_with_exponential_backoff` |
| `data_factory.py` | Faker 数据工厂 + DB 写入 + cleanup | `UserFactory` / `OrderFactory` / `TestDataManager` |
| `data_masking.py` | 敏感字段脱敏 | `DataMasker.mask_phone/email/dict_recursive` |
| `excel_generator.py` | 4 Sheet 用例 Excel + 结果 Excel | `create_testcase_excel(cases, path)` / `create_result_excel` |
| `flaky_detector.py` | junit-xml 历史归档 + flaky 检测 | `FlakyTestDetector.detect()` / `archive_junit` |
| `generate_report.py` | Word 报告 + 多端通知 webhook（企微/飞书/钉钉/Slack/邮件/Teams） | `generate_test_report(data, path)` / `send_all_notifications` |
| `jmeter_csv_exporter.py` | JMeter 参数化 CSV 生成 | `generate_jmeter_dataset(count, output)` |
| `jmeter_result_parser.py` | JTL 解析 + 性能门禁 + 基线对比 | `parse_jtl(jtl)` / `check_performance_gates` / `compare_with_baseline` |
| `regression_scope.py` | git diff 影响范围分析（YAML 配置） | `analyze_change_impact(base_branch)` |
| `zentao_bug_manager.py` | BugTracker 默认 adapter:禅道 SDK + token 续期 | `ZentaoBugManager.create_bug` / `batch_submit_from_failures` |
| `ci_quality_gate.py` | CI 门禁统一（junit + cov） | `parse_junit` / `check_smoke` / `check_regression` / `check_coverage` |
| `quality_gate_engine.py` | YAML 驱动门禁引擎（替代硬编码阈值） | `QualityGateEngine` / `check_smoke/regression/coverage/performance/release` |
| `bug_tracker_base.py` | BugTracker 抽象基类 + 工厂模式（5 适配器注册） | `BugTrackerBase` / `create_bug_manager` / `TRACKER_REGISTRY` |
| `jira_bug_manager.py` | Jira REST API 适配器 | `JiraBugManager.submit_bug/query_open_bugs` |
| `github_bug_manager.py` | GitHub Issues API 适配器 | `GitHubBugManager.submit_bug/query_open_bugs` |
| `linear_bug_manager.py` | Linear GraphQL API 适配器 | `LinearBugManager.submit_bug/query_open_bugs` |
| `webhook_bug_manager.py` | 通用 Webhook 推送适配器（企微/飞书/钉钉/Slack 回调） | `WebhookBugManager.submit_bug` |

---

## 类别 2：平台驱动（9 个）— 各平台专项

| utils 文件 | 平台 | 关键 API |
|----------|------|---------|
| `mobile_driver.py` | Android / iOS Appium 驱动 | `get_driver(platform)` / `run_monkey` / `collect_android_perf` / `archive_logcat` |
| `miniprogram_runner.py` | 微信小程序自动化 | `WxMiniProgram.open/tap/fill/screenshot` |
| `desktop_driver.py` | Windows pywinauto / macOS osascript / Electron | `get_windows_app` / `open_macos_app` / `launch_electron` / `collect_proc_perf` |
| `visual_helper.py` | 视觉测试 | `find_template(threshold)` / `ocr_image` / `compare_images(SSIM)` / `make_diff_image` |
| `iot_helper.py` | SSH + 串口 + MQTT | `SSHClient` / `open_serial` / `MQTTClient` |
| `media_validator.py` | FFmpeg 音视频校验 | `get_video_meta` / `extract_frame` / `compare_frames` / `check_audio_sync` |
| `tracing_validator.py` | Jaeger / Zipkin 链路 | `JaegerClient` / `assert_trace_complete` |
| `mq_helper.py` | Kafka / RabbitMQ | `KafkaProducerSimple` / `KafkaConsumerSimple` / `RabbitMQClient` |
| `ai_validator.py` | AI/ML 模型 + LLM | `load_predictions` / `detect_drift(KS/PSI)` / `fairness_metrics` / `llm_eval` |

---

## 类别 3：协议工具（2 个）— 横向通用，被多 utils 复用

| utils 文件 | 协议覆盖 | 关键 API |
|----------|---------|---------|
| `websocket_helper.py` | WebSocket（同步 + 异步 + 重连 + 并发） | `WSClient` / `ws_concurrent_load` / `test_reconnect` |
| `protocol_helper.py` | gRPC + TCP + UDP + GraphQL + SOAP + Modbus + 端口探活 | `grpc_call` / `tcp_send_recv` / `udp_send_recv` / `graphql_query` / `soap_call` / `modbus_*` / `is_tcp_open` |

> 其他协议归属：MQTT/SSH/串口在 `iot_helper.py`；Kafka/RabbitMQ 在 `mq_helper.py`；HTTP 在 `api_retry_util.py`；Jaeger 在 `tracing_validator.py`。

---

## 类别 4：非功能维度（6 个）— 安全 / 兼容 / 弱网 / 稳定 / 混沌 / UX

| utils 文件 | 维度 | 关键 API |
|----------|------|---------|
| `security_scanner.py` | 安全（SAST/DAST/依赖/Header/TLS） | `run_bandit` / `run_safety_check` / `check_security_headers` / `check_tls_cert` / `zap_active_scan` |
| `network_throttle.py` | 弱网（3G/4G/wifi_weak/satellite/offline） | `apply_preset(preset, mode='tc')` / `tc_apply` / `adb_throttle_emulator` / `ToxiproxyClient` |
| `chaos_helper.py` | 混沌工程 | `stress_cpu` / `stress_memory` / `stress_disk` / `kill_pod` / `block_outbound` / `shift_clock` |
| `soak_runner.py` | 长时稳定性 + 内存泄漏 | `soak_test(scenario, duration_hours, metric_proc_pid)` |
| `ux_metrics.py` | UX 量化 | `UXTracker` / `measure_tti` / `task_efficiency` / `check_ux_gates` |
| `compatibility_matrix.py` | 浏览器/OS/分辨率/语言矩阵 | `web_matrix` / `mobile_matrix` / `to_pytest_params` |

> 注：稳定性 Android Monkey 在 `mobile_driver.run_monkey`（已有，归类平台驱动）。

---

## 类别 5：用例方法（2 个）— ISTQB 经典法

| utils 文件 | 方法 | 关键 API |
|----------|------|---------|
| `state_machine_tester.py` | 状态迁移法（0/1-switch + 负例） | `StateMachine.add_transition` / `gen_0switch` / `gen_1switch` / `gen_negative` |
| `pairwise_generator.py` | 配对测试 / Allpairs | `pairwise(parameters)` / `generate_test_cases` |

## 类别 6：测试类型（2 个）— V 模型核心

| utils 文件 | 类型 | 关键 API |
|----------|------|---------|
| `bdd_runner.py` | 验收测试 BDD（Gherkin） | `create_feature_file` / `create_step_file` |
| `web_vitals_collector.py` | 前端性能 LCP/FID/CLS/INP | `collect_via_playwright` / `collect_via_lighthouse` |

## 类别 7：安全增强（2 个）— OWASP API Top 10 + Fuzzing

| utils 文件 | 维度 | 关键 API |
|----------|------|---------|
| `api_security_scanner.py` | API 安全（IDOR/SSRF/JWT/CORS/CSRF/限流） | `test_idor` / `test_ssrf` / `test_jwt_none_alg` / `test_cors` / `test_rate_limit` |
| `fuzzer.py` | 模糊测试（HTTP / 文件） | `fuzz_http_endpoint` / `fuzz_file_parser` |

## 类别 8：DB / 契约 / API（3 个）

| utils 文件 | 用途 |
|----------|------|
| `db_test_helper.py` | 事务 ACID / 死锁 / 慢查询 / 迁移 / 备份恢复 / 主从延迟 |
| `contract_test.py` | Pact 契约 / jsonschema 响应验证 |
| `openapi_test_gen.py` | OpenAPI 自动生成用例 + 全 endpoint 冒烟 |

## 类别 9：移动专项（1 个）

| utils 文件 | 用途 |
|----------|------|
| `push_test.py` | FCM / APNs 推送 + DeepLink + 安装升级 + 后台杀进程 |

## 类别 10：A11y / i18n（2 个）

| utils 文件 | 用途 |
|----------|------|
| `a11y_scanner.py` | WCAG 2.1（axe-core + Lighthouse + pa11y） |
| `i18n_checker.py` | 多语言 key 完整性 + 硬编码检测 + 文本膨胀 + RTL |

## 类别 11：度量（2 个）

| utils 文件 | 用途 |
|----------|------|
| `mutation_runner.py` | 变异测试（mutmut，验证用例有效性） |
| `dora_metrics.py` | DORA 4 大指标（部署频率 / Lead Time / 变更失败率 / MTTR） |

## 类别 12：区块链 / AI 对抗（2 个）

| utils 文件 | 用途 |
|----------|------|
| `blockchain_test.py` | Web3 + Slither 合约审计 + Foundry invariant + Gas 回归 |
| `ai_adversarial.py` | 对抗样本（FGSM）+ 文本扰动 + LLM 越狱 / Prompt Injection / 隐私推断 |

---

## 类别 13：报告 / SLO / 邮件 / 减重（3 个）

| utils 文件 | 用途 |
|----------|------|
| `slo_validator.py` | SLO/SLI 性能契约 + 错误预算 + 燃烧率 |
| `email_sender.py` | SMTP 邮件直发（含附件 docx/pdf/pptx） |
| `suite_minimizer.py` | 用例去重（Jaccard 相似度）+ 覆盖率减重 |

> 报告输出 PDF / PPTX 已合并到 `generate_report.py`（generate_pdf_report / generate_pptx_summary）。

## 类别 14：输入加载（1 个）— PRD 多格式入口

| utils 文件 | 用途 | 关键 API |
|----------|------|---------|
| `prd_loader.py` | md/txt/pdf/docx/xlsx/zip/png/html/url 自动识别 + 平台路由 | `load_prd(source)` / `suggest_agents(text)` / `detect_platforms` |

---

## 测试支撑（1 个）

| utils 文件 | 用途 |
|----------|------|
| `__init__.py` | 包标识（空文件，使 utils 成为可导入包） |

---

## CLI 入口速查

每个 utils 模块均可独立 `python -m utils.<module> --help` 调用：

```bash
python -m utils.api_retry_util              # 示例（无 main）
python -m utils.jmeter_result_parser <jtl> --mode ci_quick
python -m utils.jmeter_csv_exporter --count 50
python -m utils.flaky_detector --archive ... --history ...
python -m utils.regression_scope            # 输出 git diff 平台影响 JSON
python -m utils.ci_quality_gate --smoke-xml ... --regression-xml ... --coverage-xml ...
python -m utils.generate_report --data ... --notify
python -m utils.mobile_driver monkey --package <pkg> --events 10000
python -m utils.mobile_driver collect-perf --platform android --package <pkg>
python -m utils.desktop_driver collect-perf --pid <PID>
python -m utils.visual_helper compare --current ... --baseline ...
python -m utils.visual_helper diff --current ... --baseline ... --output ...
python -m utils.visual_helper ocr --image ...
python -m utils.media_validator meta <video>
python -m utils.tracing_validator <trace_id> --required-services svc-a svc-b
python -m utils.prd_loader <source> --detect
python -m utils.websocket_helper echo --url ws://... --message ...
python -m utils.websocket_helper load --url ws://... --count 1000 --messages 10
python -m utils.protocol_helper probe --host ... --port ...
python -m utils.protocol_helper tcp/udp/graphql ...
```

---

## 添加新 utils

详见根目录 [`CONTRIBUTING.md`](../CONTRIBUTING.md) "添加新 utils" 章节。
