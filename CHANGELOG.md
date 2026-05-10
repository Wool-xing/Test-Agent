# Changelog

本文件记录 Test-Agent 工作流项目的所有可见变更。

格式参考 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

> 项目代号：`test-agent-team`（全英文内部代号）
> 中文别名：`Test-Agent 工作流搭建`

---

## [Unreleased]

### Security（安全·上架前必修 Batch 1）

- **修复 `eval()` 远程代码注入风险**：`05-代码示例/media_validator.py` 中 `get_video_meta()` 原通过 `eval(video.get("r_frame_rate"))` 解析 FFmpeg 外部输出，存在注入风险。改用 `fractions.Fraction` 安全解析。
- **移除占位邮箱**：`SECURITY.md` 与 `CODE_OF_CONDUCT.md` 移除 `security@example.com` / `conduct@example.com` 占位地址，统一指向 GitHub Security Advisories 私密通道；避免上架后被误用作真实联系方式。
- **示例脱敏**：
  - `02-专家定义/13-系统集成测试.md` 示例中 `SSHClient(host="192.168.1.100", user="root", password="...")` 改为 `os.getenv()` 读取，配合 `.env` 注入；同段 `IOT_SSH_HOST` 占位改为 `<DEVICE_IP>`。
  - `02-专家定义/07-测试执行.md` 混沌命令示例中真实风格 IP `192.168.1.100` 改为占位 `<TARGET_IP>`。

### Changed（数字漂移修复 + URL 统一 Batch 2）

- **顶层文档数字一致性**：`8 位专家 / 9 agent / 8 skill / 12 utils` 等过时数字全栈修正为 `14 agent / 13 skill / 49 utils`（核心 8 专家 + 平台扩展 5 专家 + test-lead 协调者）。涉及：`README_DETAIL.md` / `01-快速开始/使用手册.md` / `02-专家定义/01-测试主管.md` / `03-技能定义/test-coordinator.md` / `install.sh`。
- **GitHub 仓库 URL 统一**：所有引用 `YOUR-USER/Test-Agent工作流搭建` 的位置统一为 `Wool-xing/Test-Agent`（权威英文仓库名；中文 `Test-Agent工作流搭建` 仅作目录别名）。fork 用户可用 `TEST_AGENT_REPO_URL` 环境变量覆盖。涉及：`01-快速开始/部署说明.md` / `01-快速开始/使用手册.md` / `README_DETAIL.md`。
- **覆盖率口径统一为 ~95%**：原 `~99%` (README/README_DETAIL) vs `约 90%` (00-项目导航) 不一致，统一为 `~95%`，剩 5% 为高度专业合规领域（航空 DO-178C / 医疗 HIPAA / 工业控制 IEC61508）。

### Added

- 新建 `CHANGELOG.md` + `VERSION` 文件，启动语义版本管理。
- **W3 信息架构重塑**：
  - `README_DETAIL.md` 改名为 `FULL_GUIDE.md`（宪章§0 文件分发策略：README.md 简明入口 ≤ 200 行 / FULL_GUIDE.md 详细指南）
  - 新建 `01-快速开始/INDEX.md` / `04-配置文件/INDEX.md` / `06-CICD集成/INDEX.md`（宪章§3 每目录索引；02/03/05 已有 README.md 等价于 INDEX）
  - `README.md` 头加项目代号 `test-agent-team` + 版本 + License
  - `README.md` 删除三视角矩阵段（迁移至 FULL_GUIDE.md，避免双份维护）
  - `README.md` 行数从 240 降至 168 行
- **W3 安全增强**：
  - `49 个 utils .py` 文件头加 `# SPDX-License-Identifier: MIT`（合规标识）
  - `.pre-commit-config.yaml` 加 gitleaks hook（凭据扫描）
  - `.gitignore` 补漏：`.ruff_cache/` / `*.jtl` / `*.pem` / `*.key` / `*.crt` / `*.p12` / `*.pfx` / `*.jks` / `id_rsa` / `id_ed25519` / `coverage.xml` / `pip-wheel-metadata/`
- **W3 收尾 · 方法论沉淀（F'+J+K）**：
  - `CONTRIBUTING.md` 末尾追加：**同步铁律段**（联动改动清单速查 + 自动化保障）+ **RACI 协作矩阵浓缩版**（14 专家 × 35 测试维度，含责任边界冲突解决与质量门禁联动）
  - `FULL_GUIDE.md` 末尾追加：**测试架构合理性深度章节**（6 子节：金字塔 2024 现代版 / Shift-Left 7 层 / Shift-Right 9 层 / 可观测三柱 + 测试可视化 / 五层质量门禁 + Flaky vs Reruns 哲学 / 调整路径 Phase 2-4 落地点）
  - 新建 `examples/web-demo/`：8 文件最小可跑 Web 测试示例（pytest + Playwright + Page Object，演示 `https://playwright.dev`，5 分钟跑通）
  - `FULL_GUIDE.md:395` 漏修补救：`utils/*.py（12 个）` → `49 个，含 __init__.py`

### Notes

W1+W2+W3 合并提交：上架前必修安全 + 数字漂移修复 + URL 统一 + 信息架构重塑（FULL_GUIDE/INDEX/SPDX/gitleaks）。
后续 W4 博客 + Show HN 准备 待执行。

> 注：本仓库 GitHub Actions CI 已配 `permissions: contents: read` 最小权限（F3）；CodeQL 显式声明 per-job 权限。pre-commit 已含 `detect-private-key` + 私有源 MD 防护 + .env 防护 + 14/13/49 文件统计。

---

---

## [1.0.0] - 2026-05-10

### Added

- 14 测试专家 Agent（核心 9 + 平台扩展 5）
- 13 测试技能 Skill（通用 8 + 平台 5）
- 49 utils Python 工具模块
- GitHub Actions + Jenkins 双 CICD
- Dependabot 周扫描 + pip-audit/safety CVE 拦截
- 多格式 PRD 加载（md/pdf/docx/xlsx/zip/png/url/html/pptx）
- MCP filesystem 通道；zentao/wechat/feishu/dingtalk MCP 教程骨架
- install.sh 一键远程部署
- LICENSE (MIT) / SECURITY.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md
