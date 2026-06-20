# CHANGELOG — Test-Agent V2.0.0

> **发布日期：** 2026-06-20
> **格式参考：** [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)
> **版本规范：** [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)
> **仓库：** [github.com/Wool-xing/Test-Agent](https://github.com/Wool-xing/Test-Agent)

---

## [2.0.0] — 2026-06-20

V2.0.0 是一次架构级重构。从 V1.x 的"文档+工具箱"模式全面升级为 **ManifestV2 单源真理架构**，引入 Rust 执行引擎、Textual TUI 操控面板、Plugin SDK、ImpactEngine 知识图谱冲击分析等核心子系统。测试覆盖 238 条（179 条 V2 新增 + 59 条留存），回归 0。

### Added

#### 架构与基础设施
- **ManifestV2 单源真理** — Pydantic 验证的 `specs/` 目录，统一 16 Agent + 32 Skill 的定义源（#381）
- **Rust 执行引擎** — `engine/` 目录，含 `tagent-engine` 核心 + `tagent-pyo3` Python 绑定（pyo3 0.29），拓扑排序 DAG 并行执行，23 项 Rust 测试（#381, #390210d）
- **Plugin SDK v1** — `sdk/` 目录，含 scaffold / validate / install / list / uninstall 五命令（#381）
- **ImpactEngine** — 知识图谱驱动的变更冲击分析，基于 graphify 5,388 节点图谱进行 blast radius 查询（#381）
- **Knowledge Graph** — 全项目 graphify 知识图谱，覆盖 runtime/ + utils/ + ai/ 共 8,902 条边（#371）

#### CLI & TUI
- **Textual TUI 面板** — 10 个实时面板：执行监控、趋势图、搜索、皮肤切换、Agent 状态、Skill 状态、系统健康、日志流、Git 状态、上下文用量（#404, #405, #406）
- **TUI 皮肤系统** — default / dark / minimal / retro 四套主题，实时切换（#404）
- **Rich 状态栏** — provider:model | project | git:branch | health | context% 动态显示（#397）
- **TUI 交互增强** — Ctrl+L 清屏、终端标题 OSC 转义、rprompt 右对齐、彩色上下文计量表（#397）
- **模型自动路由** — LIGHT/HEAVY 任务分级，6 provider 双 tier，中转站兼容（#397）
- **流式输出** — DAG 执行进度实时 Rich Live table，direct + Prefect 双路径（#397）

#### Agent & Skill
- **Intent Router v2** — AI/CLI 共享路由，ManifestV2 catalog + 关键词 fallback（#381）
- **ExecutionContext** — 线程安全执行上下文，替代全局 `_upstream_outputs`（#381）
- **Sprint 1 基础技能** — 5 项可验证基础技能：ping-check / http-check / file-check / process-check / timeout-check（#400）
- **Agent 引擎验证** — 16 Expert + 32 Skill + DAG 9/9 全链路验证通过（#401）
- **统一命令注册表** — NL 触发器 + 双语帮助，所有 slash command 统一管理（#337）

#### 平台与安全
- **平台沙箱抽象** — Linux Landlock / macOS Seatbelt / Windows Job Object 三层隔离（#381）
- **SessionStore** — SQLite + FTS5 全文本搜索，跨会话学习循环（#381）
- **SSO + RBAC** — OIDC/SAML 单点登录 + 4 角色 7 权限（#381）
- **SHA-256 哈希链审计追踪** — 防篡改证据链（#381）
- **多租户数据隔离** — 工作空间级租户分离（#381）
- **Tauri 2 桌面壳** — 替代 Electron，~10MB 二进制，Windows/macOS/Linux（#381）
- **VitePress 文档站点** — 5 页文档网站（#381）
- **Marketplace Web UI** — React 18 + Vite 5 + shadcn/ui，4 页（#381）

#### CI/CD
- **18-job GitHub Actions CI** — 三平台矩阵 + manifest 验证（#381）
- **Brew Formula** — macOS Homebrew 安装支持（#405）

### Changed

- **VERSION 系统统一** — `VERSION` 文件为单源，`runtime.__version__` 同步读取（#381）
- **Agent/Skill 定义迁移** — 从 `.md` frontmatter 迁移至 `specs/*/manifest.yaml` 单源真理（#381）
- **CONTRIBUTING.md 更新** — 适配 V2 manifest 驱动工作流（#381）
- **所有文档数字升级** — 16 agent / 32 skill / 92 utils，去除 V1.x 历史印记（#381）
- **CLI 启动噪声抑制** — LiteLLM / Prefect / loguru 第三方日志降为 ERROR（#397）
- **pydantic 依赖** — `>=2.0` 升级至 `>=2.13.4`（#392）

### Fixed

- **27 项安全漏洞修复** — Dependabot + CodeQL 根因修复（#84c917b, #2716e0c, #76ba107）
- **6 项 V2.0.0 打磨 bug** — 部署路径断裂、LLM 配置硬编码、TUI HTML 兼容性、log 噪声、LICENSE 缺失等（#397）
- **CI 多项实现 bug** — Router/FlowRegistry 类名、mcp 变量、API 函数名、tasks.py 可选导入、flows.py 优雅降级等（#329, #330, #331, #332, #333, #334, #335, #336）
- **CI macOS 安装计数** — skill count 32→37 同步（#403）
- **缺少 `_BUILTIN_MAP` 定义** — 测试断言同步修复（#360）
- **Sprint 0 复杂度分解** — 7 项 CRITICAL 复杂度函数分解（CC=42→11 等），大文件拆分（1864→79 行 facade + 4 子文件）（#399）
- **完整 E2E 验证** — 30 步验证流程：PRD → Route(5 nodes) → DAG → Execute → Gate → Audit（#397）

### Removed

- **内部行话标记** — 主宪章/铁律/铭文/三公理/灵魂底色/熄火 等从所有代码注释中移除（#381）
- **V1.x rollout 历史印记** — 所有 docstring 中的 `[V1.x rollout]` 标记替换为 `[unimplemented]`（#381）
- **全局 `_upstream_outputs`** — 被 ExecutionContext 替代（#381）
- **charter/§/hermes/gbrain 装饰性标记** — 从代码和注释中清除（#381）
- **内部治理标签** — CI 工作流名称中移除（#359）

### Security

- **markdownlint 全面修复** — 20,201 条警告降至 0，新增 `.markdownlint.json` 配置（#381, #b955fdd）
- **依赖漏洞修复** — Dependabot 批量升级（selenium / bandit / pytest 生态）（#361, #362, #363）
- **安全清理** — 27 项 CodeQL + Dependabot 根因修复（#84c917b）
- **Rust 编译安全** — pyo3 0.29 兼容 + workspace 配置，Cargo audit 通过（#390210d）
- **三层路径消毒** — string guard + os.path.abspath + prefix check（#22fd374）

---

## 破坏性变更

1. **全局 `_upstream_outputs` 已移除。** 下游代码若直接引用该全局变量将报 `AttributeError`。使用 `ExecutionContext` 替代 —— 导入 `from runtime.context import ExecutionContext`。
2. **Agent/Skill 定义格式变更。** 新 Agent/Skill 必须编写 `specs/*/manifest.yaml` 而非仅 `.md` frontmatter。V1 格式 Agent/Skill 仍可被 registry 读取（兼容模式），但新功能仅在 ManifestV2 路径上开发。
3. **VERSION 读取方式。** 直接读取 `VERSION` 文件的代码需改为 `from runtime import __version__`。

## 废弃通知

- `scripts/migrate_to_v2.py` 提供 V1→V2 迁移脚本，后续版本将移除对 `.md` frontmatter 的兼容读取。
- `runtime/orchestrator/adapters/experts.py` 中的 `SCRIPT_MAP` fallback 路径标记为 deprecated，计划在 V2.1.0 移除。
- `_upstream_outputs` 残余引用在 7 个 agent docstring 中保留为注释，下一版将清理。

## V1.x 迁移指南

1. **运行迁移脚本：** `python scripts/migrate_to_v2.py` — 将 V1 `.md` frontmatter 转换为 `specs/` 结构。
2. **替换全局变量：** 将所有 `_upstream_outputs` 引用改为 `ExecutionContext` 实例。
3. **更新安装：** 删除旧 `.venv`，重新运行 `python install.py <project-dir>`。
4. **验证 manifest：** `tagent doctor --manifests` 确认 48/48 manifest 加载通过。
5. **运行测试：** `pytest runtime/tests/ -v` 确认 238 条测试全绿。

> 完整迁移文档见 [`docs/v2.0.0/02-架构设计/`](../02-架构设计/) 及 [`scripts/migrate_to_v2.py`](../../../scripts/migrate_to_v2.py)。

---

## 历史版本

- [v1.43.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.43.0) — 2026-05-19
- [v1.37.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.37.0) — 2026-05-18
- [v1.36.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.36.0) — 2026-05-18
- [v1.35.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.35.0) — 2026-05-18
- [v1.34.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.34.0) — 2026-05-18
- [v1.0.0](https://github.com/Wool-xing/Test-Agent/releases/tag/v1.0.0) — 2026-05-10

完整历史见仓库根目录 [`CHANGELOG.md`](../../../CHANGELOG.md)。
