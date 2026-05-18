<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🌐 全链路覆盖矩阵（三视角）

> ⚠️ **状态标记释义**：✅ = 定义/工具链已存在（含 utils + agent .md + skill .md），不保证已端到端真 LLM 验证。
> 完整实装状态见 [ROADMAP.md](../../ROADMAP.md) frontmatter `IMPL_STATUS`。

### 矩阵 A：产品形态覆盖

| 产品形态 | 工具栈 | 责任 Agent | 关联 Skill | 状态 |
|---------|-------|-----------|----------|------|
| Web（PC + 移动 H5） | Playwright | automation-engineer | `/python-script-gen` | ✅ |
| REST / GraphQL / SOAP API | requests / protocol_helper | automation-engineer | `/python-script-gen` | ✅ |
| Android APP | Appium + adb | mobile-tester | `/mobile-test` | ✅ |
| iOS APP | Appium + XCUITest | mobile-tester | `/mobile-test` | ✅ |
| 微信 / 支付宝 / 抖音小程序 | 微信开发者工具 CLI | mobile-tester | `/mobile-test` | ✅ |
| Windows EXE | pywinauto + uiautomation | desktop-tester | `/desktop-test` | ✅ |
| macOS .app | PyAutoGUI + AppleScript | desktop-tester | `/desktop-test` | ✅ |
| Linux GUI | atspi + xdotool | desktop-tester | `/desktop-test` | ✅ |
| Electron 跨平台 | Playwright Electron API | desktop-tester | `/desktop-test` | ✅ |
| 游戏 / Canvas / WebGL / Unity | Airtest + OpenCV | visual-tester | `/visual-test` | ✅ |
| IoT / 嵌入式 | SSH + 串口 + MQTT + Modbus | system-tester | `/system-test` | ✅ |
| 音视频 / 流媒体 | FFmpeg + ffprobe | system-tester | `/system-test` | ✅ |
| AI / ML 模型 + LLM | scikit-learn + scipy + LLM eval | ai-tester | `/ai-test` | ✅ |
| 区块链 / 智能合约 | Web3 + Slither + Foundry | system-tester | `/system-test` | ✅ |
| 数据库 | SQLAlchemy + db_test_helper | data-preparer | `/data-preparation` | ✅ |

### 矩阵 B：测试类型覆盖

| 测试类型 | 工具 / utils | 责任 Agent | 状态 |
|---------|------------|-----------|------|
| 功能（unit / integration / e2e / UAT BDD） | pytest + pytest-mock + pytest-bdd | automation-engineer | ✅ |
| 性能（基准/负载/压力/Volume/Spike/Soak/SLO） | JMeter + Locust + slo_validator + soak_runner | test-executor | ✅ |
| 安全（SAST/DAST/依赖/Header/TLS/API/Fuzzing） | Bandit + Safety + ZAP + Burp Pro + api_security_scanner + fuzzer | bug-manager | ✅ |
| 兼容（浏览器/OS/分辨率/语言矩阵） | compatibility_matrix（pairwise） | testcase-designer | ✅ |
| 弱网（3G/4G/wifi_weak/satellite/offline） | tc + Toxiproxy + network_throttle | test-executor | ✅ |
| 稳定（Android Monkey + 长时 soak + 内存泄漏） | mobile_driver.run_monkey + soak_runner | mobile-tester | ✅ |
| 可靠性（重连/重试/降级/熔断） | api_retry_util + 业务故障注入 | automation-engineer | ✅ |
| 混沌（CPU/内存/磁盘/网络/进程/k8s） | chaos_helper | test-executor | ✅ |
| 灾备 / Failover | chaos_helper.kill_pod + 数据一致性校验 | test-executor | ✅ |
| UX（任务时长/点击数/TTI/恢复率） | ux_metrics.UXTracker | testcase-designer | ✅ |
| 易用性（Nielsen 10 + 角色扮演） | 人工 walkthrough | testcase-designer | ✅ |
| 探索性（SBTM session + heuristics） | charter 模板 + 录屏 | testcase-designer | ✅ |
| 前端性能 Web Vitals（LCP/FID/CLS/INP） | web_vitals_collector | automation-engineer | ✅ |
| A11y 无障碍（WCAG 2.1） | a11y_scanner（axe + Lighthouse + pa11y） | testcase-designer | ✅ |
| 国际化 / 本地化（多语言/RTL） | i18n_checker | testcase-designer | ✅ |
| 数据库（事务/死锁/迁移/备份恢复/主从） | db_test_helper | data-preparer | ✅ |
| 契约测试（Pact / jsonschema） | contract_test + openapi_test_gen | automation-engineer | ✅ |
| 视觉回归（SSIM + OCR + diff） | visual_helper | visual-tester | ✅ |
| AI 对抗 / LLM 越狱 / Prompt Injection | ai_adversarial | ai-tester | ✅ |
| 变异测试（用例有效性） | mutation_runner | testcase-designer | ✅ |
| DORA 4 指标 + 缺陷密度 + 套件减重 | dora_metrics + suite_minimizer | bug-manager | ✅ |
| 伦理 / 偏见审计（数据集/模型/决策公平性） | fairness_auditor.py + ai_adversarial + suite_minimizer（覆盖偏差） + 公平性指标 | ai-tester | ✅ |
| 沉默故障检测（无报警的恶化） | silent_failure_detector.py + tracing_validator + web_vitals_collector + 阈值漂移检测 | test-executor | ✅ |
| 决策可回放（任一判断可复现可反驳） | tracing_validator + history 归档 + 模型版本快照 | test-lead | ✅ |
| 缺席者场景注入（残障/老年/未成年/未联网/精神危机） | a11y_scanner + i18n_checker + 边缘场景剧本库 | testcase-designer | ⚪ Phase 3 |
| 证据链可采信性（司法/审计/监管送审） | dora_metrics + tracing_validator + 决策日志打包 | bug-manager | ⚪ Phase 4 |
| 神圣性与跨文化禁忌边界（宗教/葬礼/儿童/纪念） | i18n_checker + 禁忌词/色/数/节日组合（本地化共建） | testcase-designer | ⚪ Phase 5 |
| Skill 自进化（darwin-skill 双重评估 + 棘轮） | darwin-skill SKILL.md + results.tsv + 子 agent 实测 | test-lead 触发 | ✅ |
| Bug 工具多适配（5 套 tracker 全部实装） | bug_tracker_base + zentao/jira/github/linear/webhook_bug_manager | bug-manager | ✅ |
| Agent 协作纪要（讨论/反问/通信落档） | agentchat_recorder + workspace/执行日志/discussions/ | test-lead | ✅ |

### 矩阵 C：用例设计方法（ISTQB 经典）

| 方法 | 实现 | 责任 Agent | 状态 |
|------|------|-----------|------|
| 等价类划分 / 边界值 | 文档 + Excel 模板 | testcase-designer | ✅ |
| 判定表 / 因果图 | 文档手动 + Excel | testcase-designer | ✅ |
| 场景法 / 错误推测 | 文档 | testcase-designer | ✅ |
| 状态迁移法（0/1-switch + 负例） | state_machine_tester | testcase-designer | ✅ |
| 配对测试（Allpairs） | pairwise_generator | testcase-designer | ✅ |
| 正交实验法 | compatibility_matrix（隐含） | testcase-designer | ✅ |
| 探索性测试（SBTM） | charter 模板 | testcase-designer | ✅ |
| 易用性走查（Nielsen 10） | 人工 + 检查清单 | testcase-designer | ✅ |
| 基于风险的测试 | 风险矩阵文档 | test-lead | ✅ |

### 矩阵 D：协议覆盖

| 协议 | 实现 utils | 状态 |
|------|----------|------|
| HTTP / HTTPS | api_retry_util | ✅ |
| WebSocket（同步/异步/重连/并发） | websocket_helper | ✅ |
| gRPC / TCP / UDP / GraphQL / SOAP / Modbus | protocol_helper | ✅ |
| MQTT / SSH / 串口 | iot_helper | ✅ |
| Kafka / RabbitMQ | mq_helper | ✅ |
| Jaeger / Zipkin（链路追踪） | tracing_validator | ✅ |

### 测试金字塔分布

```text
        E2E（10%）         ← Playwright/Appium，慢但必要
       /集成（20%）/        ← API + 服务间 + Mock
      /单元（70%）/         ← pytest + pytest-mock，秒级反馈
```

**总覆盖率 ~90%**（含闭环：Bug 多适配 + 多端通知 + CI/CD GitHub Actions/Jenkins + Dependabot）

剩 ~10% 为高度专业合规领域（HIPAA 医疗 / SOC2 金融 / DO-178C 航空 / IEC61508 工业控制）—— 业务方按需自加。

---
