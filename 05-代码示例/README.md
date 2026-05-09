# 05-代码示例（utils/）索引

24 个 Python 工具模块（含 `__init__.py`），按职责四分类。

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
| `generate_report.py` | Word 报告 + 三端通知 webhook | `generate_test_report(data, path)` / `send_all_notifications` |
| `jmeter_csv_exporter.py` | JMeter 参数化 CSV 生成 | `generate_jmeter_dataset(count, output)` |
| `jmeter_result_parser.py` | JTL 解析 + 性能门禁 + 基线对比 | `parse_jtl(jtl)` / `check_performance_gates` / `compare_with_baseline` |
| `regression_scope.py` | git diff 影响范围分析（YAML 配置） | `analyze_change_impact(base_branch)` |
| `zentao_bug_manager.py` | 禅道 SDK + token 续期 | `ZentaoBugManager.create_bug` / `batch_submit_from_failures` |
| `ci_quality_gate.py` | CI 门禁统一（junit + cov） | `parse_junit` / `check_smoke` / `check_regression` / `check_coverage` |

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

## 类别 4：输入加载（1 个）— PRD 多格式入口

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

## 添加新 utils 流程

1. 选定分类（核心 / 平台驱动 / 协议 / 输入加载）
2. 文件名小写下划线（如 `chaos_helper.py`）
3. 顶部 docstring 说明被引用方
4. 实现公开 API + CLI（argparse）
5. **同步**：
   - 本 README 表格加一行
   - `00-项目导航.md` 对应分类加一行
   - `04-配置文件/requirements.txt` 加新依赖
   - `04-配置文件/.env.example` 加配置字段
   - `04-配置文件/conftest.py` `pytest_configure` 加产出目录
   - `04-配置文件/pytest.ini` markers 加新标记
   - `install.sh` + `01-快速开始/部署说明.md` 拷贝清单加文件名
   - 源 MD `Test-Agent工作流搭建.md` 内嵌段
