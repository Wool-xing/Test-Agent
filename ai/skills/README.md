# skills 索引

**32 业务 Skill + 3 元 Skill**。

业务 skill 按领域分:通用流程 8 + 平台专项 5 + 渗透安全 7 + 车载 5 + ECC 测试加固 6 + 探索学习 1 = 32。
元 skill 3 个子目录:`darwin-skill/` `karpathy-guidelines/` `nuwa-skill/` — 用法见各子目录 SKILL.md。

顶层导航见根目录 [00-项目导航.md](../../00-项目导航.md);路线图见 [ROADMAP.md](../../ROADMAP.md)。

---

## 类别 1：通用流程 8 Skill

| Skill | 文件 | 用途 | 触发示例 |
| ------- | ----- | ------ | --------- |
| `/smoke-test` | `smoke-test.md` | P0 冒烟（≥95% 门禁，11min 上限） | 上线前快速验证 |
| `/test-coordinator` | `test-coordinator.md` | 完整流程编排（自动平台路由） | 新功能完整测试 |
| `/regression-test` | `regression-test.md` | P0+P1 回归 + Flaky + JMeter | 迭代发布前 |
| `/testcase-design` | `testcase-design.md` | 4 Sheet Excel 用例 | 评审前 / 手测前 |
| `/python-script-gen` | `python-script-gen.md` | pytest UI/API 脚本生成 | 用例转自动化 |
| `/jmeter-script-gen` | `jmeter-script-gen.md` | JMeter JMX 性能计划（双模式 ci_quick/full） | 性能测试 |
| `/data-preparation` | `data-preparation.md` | 测试数据 + JMeter CSV 生成 | 测试前数据准备 |
| `/zentao-bug-submission` | `zentao-bug-submission.md` | BugTracker 规范提交（默认禅道示例,可换 Jira/GitHub/GitLab/Linear/Webhook,见 `BUG_TRACKER` env） | 失败用例后 |

---

## 类别 2：平台专项 5 Skill（按产品形态选）

| Skill | 文件 | 平台 | 必装外部依赖 |
| ------- | ----- | ------ | ------------- |
| `/mobile-test` | `mobile-test.md` | Android / iOS / 微信/支付宝小程序 | Appium server / Android SDK / Xcode / 微信开发者工具 |
| `/desktop-test` | `desktop-test.md` | Windows EXE / macOS .app / Linux GUI / Electron | pywinauto（Win） / pyautogui / Playwright |
| `/visual-test` | `visual-test.md` | 游戏 / Canvas / WebGL / OCR / 视觉回归 | Airtest / Tesseract / OpenCV |
| `/system-test` | `system-test.md` | IoT / 音视频 / 链路追踪 / 消息队列 | FFmpeg / Jaeger / Kafka 或 RabbitMQ |
| `/ai-test` | `ai-test.md` | AI/ML 模型 / LLM 应用 | 推理服务 endpoint / LLM API |

---

---

## 类别 3：渗透安全 7 Skill

| Skill | 文件 | 用途 | 触发示例 |
| ------- | ----- | ------ | --------- |
| `/pentest-coordinator` | `pentest-coordinator.md` | 渗透测试总协调（自动路由子 skill） | 安全测试启动 |
| `/pentest-recon` | `pentest-recon.md` | 信息收集与资产侦察 | 渗透前信息收集 |
| `/pentest-vuln` | `pentest-vuln.md` | 漏洞扫描与验证 | 自动化漏洞检测 |
| `/pentest-exploit` | `pentest-exploit.md` | 漏洞利用与 PoC 验证 | 漏洞复现 |
| `/pentest-web` | `pentest-web.md` | Web 应用渗透（OWASP Top 10） | Web 安全测试 |
| `/pentest-api` | `pentest-api.md` | API 渗透测试（JWT/OAuth/GraphQL） | API 安全测试 |
| `/pentest-report` | `pentest-report.md` | 渗透测试报告生成 | 安全评估输出 |

## 类别 4：车载 5 Skill

| Skill | 文件 | 用途 | 触发示例 |
| ------- | ----- | ------ | --------- |
| `/automotive-test` | `automotive-test.md` | 车载测试总协调 | 车载系统测试 |
| `/automotive-can-bus-test` | `automotive-can-bus-test.md` | CAN 总线协议测试 | CAN 报文验证 |
| `/automotive-adas-scenario` | `automotive-adas-scenario.md` | ADAS 场景测试 | 辅助驾驶验证 |
| `/automotive-hil-loop-test` | `automotive-hil-loop-test.md` | HIL 硬件在环测试 | 硬件在环验证 |
| `/automotive-ota-update-test` | `automotive-ota-update-test.md` | OTA 升级测试 | 远程升级验证 |

## 类别 5：ECC 测试加固 6 Skill

| Skill | 文件 | 用途 | 触发示例 |
| ------- | ----- | ------ | --------- |
| `/tdd-workflow` | `tdd-workflow.md` | 测试驱动开发工作流 | 新功能开发 |
| `/e2e-testing` | `e2e-testing.md` | 端到端测试（Playwright） | 关键用户流程 |
| `/verification-loop` | `verification-loop.md` | 验证循环（自检+修复） | 持续质量检查 |
| `/eval-harness` | `eval-harness.md` | 评估框架（LLM-as-judge） | AI 输出质量评估 |
| `/security-review` | `security-review.md` | 安全代码审查 | 代码提交前安全检查 |
| `/agent-introspection-debugging` | `agent-introspection-debugging.md` | Agent 自省调试 | Agent 行为异常排查 |

## 类别 6：探索学习 1 Skill

| Skill | 文件 | 用途 | 触发示例 |
| ------- | ----- | ------ | --------- |
| `/build-your-own-x-explorer` | `build-your-own-x-explorer.md` | 探索式学习（BYO-X 框架） | 新技术评估 / 实验 |

## 元 Skill 3 个（子目录）

| 元 Skill | 目录 | 用途 |
| ---------- | ------ | ------ |
| `darwin-skill` | `darwin-skill/` | Skill 自进化机制优化 |
| `karpathy-guidelines` | `karpathy-guidelines/` | Karpathy 编码纪律注入 |
| `nuwa-skill` | `nuwa-skill/` | 女娲：人物思维框架蒸馏 |

---

## 每个 Skill 文件结构

每个 skill 文件统一包含以下章节：

1.**YAML frontmatter**（name / description / tools）
2.**🔔 开测前准备清单**（平台 skill 含此段，列必备 + 可选项）
3.**触发方式**（`/skill-name`）
4.**适用场景**
5.**执行流程**（Step 1, 2, 3...）
6.**质量门禁**
7.**输出文件**

---

## 添加新 Skill

详见根目录 [`CONTRIBUTING.md`](../../CONTRIBUTING.md) "添加新 Skill" 章节。
