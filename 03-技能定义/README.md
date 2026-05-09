# 03-技能定义 索引

13 个 Skill，分两类：通用流程 + 平台专项。

> 顶层导航见根目录 `00-项目导航.md`。

---

## 类别 1：通用流程 8 Skill

| Skill | 文件 | 用途 | 触发示例 |
|-------|-----|------|---------|
| `/smoke-test` | `smoke-test.md` | P0 冒烟（≥95% 门禁，11min 上限） | 上线前快速验证 |
| `/test-coordinator` | `test-coordinator.md` | 完整流程编排（自动平台路由） | 新功能完整测试 |
| `/regression-test` | `regression-test.md` | P0+P1 回归 + Flaky + JMeter | 迭代发布前 |
| `/testcase-design` | `testcase-design.md` | 4 Sheet Excel 用例 | 评审前 / 手测前 |
| `/python-script-gen` | `python-script-gen.md` | pytest UI/API 脚本生成 | 用例转自动化 |
| `/jmeter-script-gen` | `jmeter-script-gen.md` | JMeter JMX 性能计划（双模式 ci_quick/full） | 性能测试 |
| `/data-preparation` | `data-preparation.md` | 测试数据 + JMeter CSV 生成 | 测试前数据准备 |
| `/zentao-bug-submission` | `zentao-bug-submission.md` | 禅道 Bug 规范提交 | 失败用例后 |

---

## 类别 2：平台专项 5 Skill（按产品形态选）

| Skill | 文件 | 平台 | 必装外部依赖 |
|-------|-----|------|-------------|
| `/mobile-test` | `mobile-test.md` | Android / iOS / 微信/支付宝小程序 | Appium server / Android SDK / Xcode / 微信开发者工具 |
| `/desktop-test` | `desktop-test.md` | Windows EXE / macOS .app / Linux GUI / Electron | pywinauto（Win） / pyautogui / Playwright |
| `/visual-test` | `visual-test.md` | 游戏 / Canvas / WebGL / OCR / 视觉回归 | Airtest / Tesseract / OpenCV |
| `/system-test` | `system-test.md` | IoT / 音视频 / 链路追踪 / 消息队列 | FFmpeg / Jaeger / Kafka 或 RabbitMQ |
| `/ai-test` | `ai-test.md` | AI/ML 模型 / LLM 应用 | 推理服务 endpoint / LLM API |

---

## 每个 Skill 文件结构

每个 skill 文件统一包含以下章节：

1. **YAML frontmatter**（name / description / tools）
2. **🔔 开测前准备清单**（平台 skill 含此段，列必备 + 可选项）
3. **触发方式**（`/skill-name`）
4. **适用场景**
5. **执行流程**（Step 1, 2, 3...）
6. **质量门禁**
7. **输出文件**

---

## 添加新 Skill 流程

1. 选定分类（通用 / 平台专项）
2. 文件名 `<verb>-<noun>.md`（如 `chaos-test.md`）
3. 顶部 YAML frontmatter
4. 加准备清单 + 流程 + 门禁
5. **同步**：
   - 本 README 加一行
   - `00-项目导航.md` 加一行
   - `01-快速开始/使用手册.md` skill 详解段加描述
   - `02-专家定义/01-测试主管.md` 快速命令清单加一行
   - `install.sh` + `部署说明.md` 拷贝清单加文件名
   - 源 MD `Test-Agent工作流搭建.md` 内嵌段
