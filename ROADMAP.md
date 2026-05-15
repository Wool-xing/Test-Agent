# Test-Agent V1.x ROADMAP

> 项目终态目标:每个 expert / skill 真 LLM-driven / script-backed 实装,**绝不输出 mock 数据**。
> 当前状态:V1.27.0-alpha (**expert rollout 收尾 + skill rollout 进行中（5/9）**)
> - **expert 16/16 active**(11 production + 5 script);0 rollout。
> - **skill 16/32 active**(9 production + 7 script);14 处于 V1.x rollout;2 暂为 V2 vision 方法论参考。
> - 3 meta-skill(nuwa-skill / darwin-skill / karpathy-guidelines)独立,工具属性,不在 32 业务 skill 数内。
> - **V1.21.0-alpha 新增 SkillRunner 基础设施** (`runtime/orchestrator/skills/` + `SKILL_RUNNERS` registry + `@register_skill` deco + `experts.py` kind=skill 接 runner),解锁 skill 层 LLM-driven 后续 12 实装。

## 当前活跃 expert (16 / 16) — V1.x rollout 收尾

### 11 真 LLM-driven (已上线)

| Expert | 职责 |
|--------|------|
| `test-lead` | 测试主管,需求分析 → 测试策略 → 路由分发 |
| `requirements-analyst` | 需求分析(PRD 多格式加载 + 路由建议) |
| `automation-engineer` | Web/API 脚本编写 + 性能测试编排 |
| `test-executor` | 测试执行与监控 |
| `bug-manager` | Bug 提交与追踪 |
| `env-manager` | 环境检查清单 + 准备步骤(V1.15.0-alpha minimum viable) |
| `mobile-tester` | 移动测试用例 + ADB/Xcode 命令清单(V1.16.0-alpha minimum viable) |
| `visual-tester` | 视觉测试点 + 对比脚本片段 + 容差配置(V1.17.0-alpha minimum viable) |
| `system-tester` | IoT/串口/MQTT 测试用例 + 命令清单 + 协议特定配置(V1.18.0-alpha minimum viable) |
| `pentest-tester` | 5 攻击域渗透测试计划 + 工具清单 + PoC plan(V1.19.0-alpha minimum viable;仅输出计划文本,真执行守护在 utils 层 env gate) |
| `automotive-tester` | ASIL 评估 + HIL 测试 + ADAS 场景 + OTA 升级 + 合规矩阵(V1.20.0-alpha minimum viable;V1.x rollout 收尾) |

### 5 script-backed (已上线)

| Expert | 工具栈 |
|--------|--------|
| `testcase-designer` | Excel 输出测试用例 |
| `data-preparer` | Faker 生成 + 脱敏 |
| `report-generator` | Word 报告生成 |
| `desktop-tester` | pywinauto 桌面自动化 |
| `ai-tester` | eval-harness AI 模型测试 |

---

## 当前活跃 skill (24 / 32)

### 17 production (已上线)

| Skill | 类别 |
|-------|------|
| `tdd-workflow` | TDD 工作流 |
| `e2e-testing` | E2E 测试 |
| `automotive-test` | 车载主编排(V1.31.0-alpha · automotive batch) |
| `automotive-can-bus-test` | CAN总线测试(V1.31.0-alpha) |
| `automotive-adas-scenario` | ADAS场景库(V1.31.0-alpha) |
| `automotive-ota-update-test` | OTA升级测试(V1.31.0-alpha) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0-alpha) |
| `regression-test` | 回归测试 |
| `smoke-test` | 冒烟测试 |
| `testcase-design` | 用例设计 |
| `test-coordinator` | 测试流程编排 |
| `verification-loop` | 5-phase 验证循环 |
| `eval-harness` | LLM 评测编排(V1.27.0-alpha · skill rollout #5) |

### 7 script-backed (已上线)

| Skill | 工具栈 |
|-------|--------|
| `ai-test` | eval-harness AI 模型测试(utils/ai_validator) |
| `data-preparation` | Faker / data_masking / jmeter CSV |
| `desktop-test` | desktop_driver(pywinauto / AppleScript) |
| `jmeter-script-gen` | JMeter JMX 生成 |
| `python-script-gen` | pytest 脚本生成(Playwright + requests) |
| `security-review` | OWASP Top 10 + SAST + 依赖 CVE |
| `zentao-bug-submission` | BugTracker adapter(默认禅道,主宪章 §12) |

---

## V1.x rollout — 6 expert LLM-driven minimum viable 实装路线

**节奏**: 一周 1 expert,共 6 周。每完成 1 个,active 数字 +1,README 同步。
**前置**: V1.15 Day 0 — runtime/router 防 mock 改造(拒绝未实装路由,返回明确错误)。
**完成标准**: 每 expert 接 LLM 真调用 + 结构化输出(markdown/JSON),通过 3 个测试 prompt 验证。

| # | Expert | LLM-driven 实装范围(minimum viable) | 目标版本 | 状态 |
|---|--------|------------------------------------|---------|------|
| 0 | (前置) runtime/router + orchestrator 防 mock | catalog 单源 frontmatter 解析;router._validate_against_catalog warn + 降 confidence;orchestrator.execute_node 硬拒 rollout/vision/unknown(returncode=2,绝不输出 mock);expert + skill 双 layer 覆盖 | V1.14.0-alpha+1 | **done** (PR X4) |
| 1 | `env-manager` | LLM 读 PRD → 环境检查清单 + 准备步骤 markdown | V1.15.0-alpha | **done** (runtime/orchestrator/agents/env_manager.py) |
| 2 | `mobile-tester` | LLM 读 PRD + Android/iOS 上下文 → 移动测试用例 + ADB/Xcode 命令清单 | V1.16.0-alpha | **done** (runtime/orchestrator/agents/mobile_tester.py) |
| 3 | `visual-tester` | LLM 读 PRD + UI 描述 → 视觉测试点 + Playwright 视觉对比脚本 | V1.17.0-alpha | **done** (runtime/orchestrator/agents/visual_tester.py) |
| 4 | `system-tester` | LLM 读 PRD + IoT/串口/MQTT 上下文 → IoT 测试用例 + 命令清单 | V1.18.0-alpha | **done** (runtime/orchestrator/agents/system_tester.py) |
| 5 | `pentest-tester` | LLM 读 PRD + 授权检查通过 → 渗透测试计划 + 工具调用清单(生成计划,不执行攻击) | V1.19.0-alpha | **done** (runtime/orchestrator/agents/pentest_tester.py;仅输出计划文本,真执行守护已在 utils 层 `api_security_scanner.py` / `ai_adversarial.py` 用 TAGENT_PENTEST_AUTHORIZED env gate;法律责任在操作者侧,见 SECURITY.md L84) |
| 6 | `automotive-tester` | LLM 读 PRD + CAN-bus/ISO-26262 上下文 → ASIL 评估 + HIL 测试用例 | V1.20.0-alpha | **done** (runtime/orchestrator/agents/automotive_tester.py;ASIL 评估 + test_cases + bus_test_plan + adas_scenarios + ota_plan + compliance_matrix 结构化 JSON;覆盖 ECU/ADAS/IVI/V2X 4 子系统 + 8 协议 + 8 合规标准。**V1.x rollout 收尾**) |

---

## V1.x rollout — 16 skill 实装路线（含已完成 3 + 剩余 13）

**节奏**: skill rollout 起点 V1.21.0-alpha (SkillRunner 基础设施 + pentest-coordinator 首落地);后续 1 skill / PR 推进。
**完成标准**: 每 skill 接 LLM 真调用 (mock_output schema 覆盖 + production 升级 + ALL_SKILL_RUNNERS 锁规则同步)。
**前置**: ~~runtime/router 防 mock 改造 + skill 路由按 `SKILL_IMPL_STATUS` frontmatter 过滤~~ **已完成 V1.14.0-alpha+1 (PR X4)** — registry parse frontmatter + orchestrator.execute_node 拒 rollout/vision/unknown skill (returncode=2)。
**基础设施**: **V1.21.0-alpha 完成** — `runtime/orchestrator/skills/__init__.py` + `SKILL_RUNNERS` registry + `@register_skill` deco + `experts.py` kind=skill 接 skill runner (放在 SCRIPT_MAP fallback 前)。

### 通用平台 4 skill

| Skill | 范围 | 关联 expert | 状态 |
|-------|------|-------------|------|
| `mobile-test` | Android/iOS + 小程序 自动化 | mobile-tester | rollout |
| `visual-test` | 图像识别 + OCR + SSIM 视觉回归 | visual-tester | rollout |
| `system-test` | IoT/串口/MQTT/音视频/Jaeger/Kafka | system-tester | rollout |
| `eval-harness` | LLM 评测(pass@k / Jaccard / stability) | ai-tester(深化) | **done** (V1.27.0-alpha · runtime/orchestrator/skills/eval_harness.py · 5 阶段编排 + 质量门禁 + 安全护栏) |

### Pentest 7 skill(1 production / 6 rollout · 需 SECURITY.md 武器化授权 wiring 实装)

| Skill | 范围 | 状态 |
|-------|------|------|
| `pentest-coordinator` | 渗透总编排(授权 → 侦察 → 漏洞 → 利用 → 报告) | **done** (V1.21.0-alpha · runtime/orchestrator/skills/pentest_coordinator.py · 5 阶段编排 + authorization_check + subagent_pool + refuse_conditions) |
| `pentest-recon` | 侦察(被动+主动信息收集) |
| `pentest-vuln` | 漏洞发现(5 攻击域 + SAST/DAST) |
| `pentest-exploit` | 漏洞利用(沙箱 PoC,不真破坏) | **done** (V1.30.0-alpha · pentest batch 2) |
| `pentest-api` | API 渗透(OWASP API Top 10 2023) | **done** (V1.30.0-alpha · pentest batch 2) |
| `pentest-web` | Web 渗透(OWASP Top 10 + ASVS) | **done** (V1.30.0-alpha · pentest batch 2) |
| `pentest-report` | 渗透报告(仅 working PoC 入报告,shannon 哲学) | **done** (V1.30.0-alpha · pentest batch 2) |

### Automotive 5 skill

| Skill | 范围 |
|-------|------|
| `automotive-test` | 整车主编排(ECU + ADAS + IVI + V2X) | **done** (V1.31.0-alpha · automotive batch) |
| `automotive-can-bus-test` | CAN总线测试(V1.31.0-alpha) |
| `automotive-adas-scenario` | ADAS场景库(V1.31.0-alpha) |
| `automotive-ota-update-test` | OTA升级测试(V1.31.0-alpha) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0-alpha) |
| `automotive-can-bus-test` | CAN/CAN-FD/LIN/FlexRay/SOME-IP | **done** (V1.31.0-alpha · automotive batch) |
| `automotive-adas-scenario` | ADAS场景库(V1.31.0-alpha) |
| `automotive-ota-update-test` | OTA升级测试(V1.31.0-alpha) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0-alpha) |
| `automotive-adas-scenario` | ADAS 场景库 + SOTIF(ISO 21448) | **done** (V1.31.0-alpha · automotive batch) |
| `automotive-ota-update-test` | OTA升级测试(V1.31.0-alpha) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0-alpha) |
| `automotive-hil-loop-test` | HIL/SIL/MIL/PIL 环路 | **done** (V1.31.0-alpha · automotive batch) |
| `automotive-ota-update-test` | OTA 升级(UN R156 / GB 44496-2024) | **done** (V1.31.0-alpha · automotive batch) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0-alpha) |

---

## V2.x vision — 2 skill(暂留方法论参考形态)

| Skill | 当前形态 | V2 路线 |
|-------|----------|---------|
| `agent-introspection-debugging` | 方法论参考(主宪章 §28) | LLM 决策回放 + 工具调用透明化实装 |
| `build-your-own-x-explorer` | 教学引导参考(主宪章 §31) | 与 docs/theory/ 22 KB 卡片联动检索引擎 |

---

## V2.x 路线图 (longer-term)

### Skill Lifecycle 元工具改造 (适配测试领域)

- `nuwa-skill` → 测试 skill / agent 蒸馏器(改造输入域 + 蒸馏维度 + 输出模板)
- `darwin-skill` → 测试领域 8 维评分体系(重写评分维度对齐 Test-Agent 业务)

### 6 expert 深化(从 LLM-driven minimum viable → 完整 wiring)

- 接入真实工具调用(sqlmap / Burp / CAN-bus 库等)
- 自动化测试执行(不止生成计划,真跑)
- 与 marketplace 4-gate 集成
- 接入 darwin-skill 持续打分 + 周自检调度
- 接入 nuwa-skill 创建 CLI 入口 `tagent skill new <name>`

---

## 防 mock 承诺

**每个 expert / skill 实装完成前,runtime/router + orchestrator 拒绝路由,返回明确"未实装"错误**。

**绝不输出 mock 数据糊弄用户。**

V1.14.0-alpha+1 (PR X4) 起,双 layer 防 mock 已落地:
- **registry 单源**: catalog 解析 `02-专家定义/*.md` `EXPERT_IMPL_STATUS` + `03-技能定义/*.md` `SKILL_IMPL_STATUS` frontmatter,实装状态来源唯一
- **router 软警告**: `_validate_against_catalog` 检测 rollout / vision / unknown → 加 issues 并降 confidence 0.3
- **orchestrator 硬拒**: `execute_node` 对 expert / skill 任意 rollout / vision / unknown 返回 `returncode=2` + stderr "未实装",绝不走 no-op "documented step recorded" 假成功路径
- 用户路由 0 个 in-rollout expert / 14 个 in-rollout skill / 2 个 vision skill 时**收到明确说明**,而非伪装成"已运行"的 mock 输出
- 详情见 [02-专家定义/01-测试主管.md](02-专家定义/01-测试主管.md) 路由表注释

---

## 进度跟踪

| 版本 | 日期 | 完成项 | active expert 数 |
|------|------|--------|----------------|
| V1.14.0-alpha | 2026-05-13 | bundle1 信任+法律线修复;ROADMAP.md 起步 | 10/16 |
| V1.14.0-alpha+1 | 2026-05-15 | X3 数字诚实化(README/ROADMAP)+ X4 防 mock 闭环 (registry 单源 frontmatter / router warn / orchestrator hard block expert+skill 双 layer) | 10/16 |
| V1.15.0-alpha | 2026-05-15 | env-manager LLM-driven minimum viable (runtime/orchestrator/agents/env_manager.py;LLM 读 PRD → env_checks + prep_steps + dependencies + risks 结构化 JSON) | 11/16 |
| V1.16.0-alpha | 2026-05-15 | mobile-tester LLM-driven minimum viable (runtime/orchestrator/agents/mobile_tester.py;LLM 读 PRD + Android/iOS 上下文 → test_cases + device_commands + mobile_specific 结构化 JSON) | 12/16 |
| V1.17.0-alpha | 2026-05-15 | visual-tester LLM-driven minimum viable (runtime/orchestrator/agents/visual_tester.py;LLM 读 PRD + UI 描述 → visual_test_points + comparison_scripts + tolerance + baseline_strategy 结构化 JSON) | 13/16 |
| V1.18.0-alpha | 2026-05-15 | system-tester LLM-driven minimum viable (runtime/orchestrator/agents/system_tester.py;LLM 读 PRD + IoT/串口/MQTT 上下文 → test_cases + device_commands + protocol_specific + test_environment 结构化 JSON;覆盖 IoT/audiovideo/tracing/mq/integration 5 类) | 14/16 |
| V1.19.0-alpha | 2026-05-16 | pentest-tester LLM-driven minimum viable (runtime/orchestrator/agents/pentest_tester.py;LLM 读 PRD + 安全上下文 → test_mode + target_scope + recon/vuln/exploit/reporting phases 结构化 JSON;覆盖 5 攻击域 Injection/XSS/SSRF/Auth/Authz;仅输出计划文本,真执行守护在 utils 层 env gate;法律责任在操作者侧 SECURITY.md L84) | 15/16 |
| V1.20.0-alpha | 2026-05-16 | automotive-tester LLM-driven minimum viable (runtime/orchestrator/agents/automotive_tester.py;LLM 读 PRD + CAN-bus/ISO-26262 上下文 → vehicle_subsystem + asil_assessment + test_cases + bus_test_plan + adas_scenarios + ota_plan + compliance_matrix + test_environment 结构化 JSON;覆盖 ECU/ADAS/IVI/V2X 4 子系统 + 8 协议 + 8 合规标准。**V1.x rollout 收尾**) | 16/16 expert (V1.x rollout 完成) |
| V1.21.0-alpha | 2026-05-16 | **skill rollout 起点** — SkillRunner 基础设施 (runtime/orchestrator/skills/__init__.py + SKILL_RUNNERS registry + @register_skill deco + experts.py kind=skill 接 runner) + pentest-coordinator 首 skill 落地 (5 阶段编排 + authorization_check + subagent_pool + refuse_conditions). 解锁 14 rollout skill 后续流水线. | 16 expert + 8/32 production skill (15 rollout 待) |
| V1.23.0-alpha | 2026-05-16 | **skill rollout #2** — mobile-test skill 生产落地 | 16 expert + 9/32 production |
| V1.27.0-alpha | 2026-05-16 | **skill rollout #5** — eval-harness skill 生产落地 (runtime/orchestrator/skills/eval_harness.py · 5 阶段编排 + 安全护栏) | 16 expert + 9/32 production |
| V2.0.0 | TBD | V2.x 路线图启动 | 16/16 + V2 |
