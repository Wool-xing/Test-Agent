# Test-Agent V2.0.0 发布说明

> **发布日期：** 2026-06-20
> **仓库：** [github.com/Wool-xing/Test-Agent](https://github.com/Wool-xing/Test-Agent)
> **许可证：** MIT

---

## 🎉 V2.0.0：ManifestV2 架构 + Rust 引擎 + Textual TUI — 测试框架的工业化重构

Test-Agent V2.0.0 是一次从"命令式工具箱"到"声明式单源真理架构"的全面升级。
引入 ManifestV2 统一定义层、Rust 执行引擎、Textual TUI 操控面板，238 条测试 0 回归。

---

## 🆕 新功能

### CLI

| 功能 | 说明 | 相关 PR |
|------|------|---------|
| `tagent run` | 一键执行：PRD → 路由 → DAG → 执行 → 门禁 → 审计 | #381 |
| `tagent report` | Rich 格式化运行报告，含分阶段结果、产物清单 | #400 |
| `tagent catalog` | 列出 16 Expert + 32 Skill，含描述和状态 | #381 |
| `tagent doctor` | 健康检查：manifest 验证、依赖完整性、LLM 连通 | #397 |
| `tagent plugin` | Plugin SDK 管理：new / validate / install / list / uninstall | #381 |
| 模型自动路由 | LIGHT/HEAVY 任务分级，6 provider + 中转站兼容 | #397 |
| 流式输出 | DAG 执行进度实时 Rich Live table | #397 |

### TUI

| 功能 | 说明 | 相关 PR |
|------|------|---------|
| 10 面板实时终端 | 执行监控、趋势图、搜索、Agent/Skill 状态、系统健康、日志流、Git、上下文 | #404, #405, #406 |
| 4 套皮肤 | default / dark / minimal / retro，`/skin` 实时切换 | #404 |
| 动态状态栏 | provider:model \| project \| git:branch \| health \| context% | #397 |
| 上下文计量表 | 彩色 gauge（绿<60% / 黄<85% / 红>=85%），真实 tiktoken 计数 | #397 |
| rprompt 右对齐 | 模型名 + 上下文百分比右对齐显示 | #397 |
| Ctrl+L 清屏 | 刷新终端显示 | #397 |

### Agent

| 功能 | 说明 | 相关 PR |
|------|------|---------|
| ManifestV2 统一定义 | 16 Agent + 32 Skill 的 Pydantic 验证单源真理 | #381 |
| Intent Router v2 | AI/CLI 共享路由，ManifestV2 catalog + 关键词 fallback | #381 |
| ExecutionContext | 线程安全执行上下文，替代全局变量 | #381 |
| Agent 引擎验证 | 16 Expert + 32 Skill + DAG 9/9 全链路 | #401 |
| 统一命令注册表 | NL 触发器 + 双语帮助 | #337 |

### Skills

| 功能 | 说明 | 相关 PR |
|------|------|---------|
| 5 项基础测试技能 | ping-check / http-check / file-check / process-check / timeout-check | #400 |
| 32 Skill 全量加载 | 37 项（含 5 项 Sprint 1 新增），0 vision / 0 rollout | #403 |
| Skill 注册机制 | `@register_skill` 装饰器 + `SKILL_SCRIPT_MAP` 自动发现 | #401 |

### 基础设施

| 功能 | 说明 | 相关 PR |
|------|------|---------|
| Rust DAG 执行引擎 | 拓扑排序 + 并行执行，pyo3 0.29 绑定，23 项测试 | #381 |
| 平台沙箱抽象 | Linux Landlock / macOS Seatbelt / Windows Job Object | #381 |
| SessionStore | SQLite+FTS5 全文本搜索，跨会话学习 | #381 |
| ImpactEngine | 知识图谱冲击分析（5,388 节点，8,902 边） | #381, #371 |
| SSO + RBAC | OIDC/SAML 登录，4 角色 7 权限 | #381 |
| SHA-256 审计追踪 | 防篡改哈希链 | #381 |
| 多租户隔离 | 工作空间级租户数据分离 | #381 |
| Plugin SDK v1 | scaffold / validate / install / list / uninstall | #381 |
| Tauri 2 桌面应用 | ~10MB 二进制，Windows/macOS/Linux | #381 |
| VitePress 文档 | 5 页文档网站 | #381 |
| Marketplace Web UI | React 18 + Vite 5 + shadcn/ui | #381 |
| 18-job CI 流水线 | 三平台矩阵 + manifest 验证 | #381 |
| Brew Formula | macOS Homebrew 安装 | #405 |
| graphify 知识图谱 | 全项目代码结构图谱 | #371 |

---

## 🔧 Bug 修复

| 问题 | 修复内容 | 相关 PR |
|------|---------|---------|
| 27 项安全漏洞 | CodeQL + Dependabot 根因修复，含已知主机验证、eval 注入、硬编码凭据等 | #84c917b |
| 部署路径断裂 | `copy_config()` 含 `llm-providers.md` 和 `.env.minimal.example`，路径改根相对 | #397 |
| LLM 配置硬编码 | 移除 `MODEL_TIERS` 白名单，任意 LiteLLM provider 均可使用 | #397 |
| TUI HTML 兼容性 | prompt_toolkit 不支持 `<dim>` 标签，改用 `<ansigray>` 等受支持标签 | #397 |
| 第三方日志噪声 | LiteLLM / Prefect / loguru 日志降为 ERROR | #397 |
| CI 类名错误 | Router/FlowRegistry 类名不存在 → 模块导入验证 | #329 |
| CI MCP 变量缺失 | `mcp` 变量不存在 → 模块导入 | #334 |
| CI API 函数名错误 | 使用真实存在的 API 函数名 | #335 |
| settings.json 缺失 | Stop hook 缺少 hooks wrapper | #336 |
| Prefect 可选导入崩溃 | ConcurrentTaskRunner() 为 None 时优雅降级 | #331, #333 |
| 双模式 grep 误查 | 只查 import 不查其他引用 | #332 |
| 缺少 `_BUILTIN_MAP` | 定义补全，测试断言同步 | #360 |
| macOS CI 计数漂移 | skill count 32→37 同步 | #403 |
| pydantic 版本 | `>=2.0` → `>=2.13.4` | #392 |
| Sprint 0 复杂度爆炸 | 7 项 CRITICAL 复杂度函数分解，大文件拆分 | #399 |
| 依赖漏洞批量升级 | selenium / bandit / pytest 生态各组 | #361, #362, #363 |

---

## ⚠️ 破坏性变更

### 1. `_upstream_outputs` 全局变量已移除

**影响：** 任何直接引用 `_upstream_outputs` 的代码将抛出 `AttributeError`。

**迁移：**
```python
# V1.x (已废弃)
from runtime.orchestrator.adapters.experts import _upstream_outputs
data = _upstream_outputs.get("key")

# V2.0.0
from runtime.context import ExecutionContext
ctx = ExecutionContext()
data = ctx.get_upstream("key")
```

### 2. Agent/Skill 定义格式变更

**影响：** 新定义必须写入 `specs/*/manifest.yaml`（Pydantic 验证），`.md` frontmatter 仅兼容读取。

**迁移：** 运行 `python scripts/migrate_to_v2.py` 自动转换。

### 3. VERSION 读取方式

**影响：** 直接读 `VERSION` 文件的代码不受影响，但推荐统一入口。

**迁移：**
```python
# 旧方式（仍可用）
with open("VERSION") as f:
    version = f.read().strip()

# 推荐方式
from runtime import __version__
```

---

## 📦 安装

### 方法 1：一键安装脚本（推荐）

```bash
# Linux / macOS
curl -fsSL -o install.py https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py
python install.py ~/test-agent-project

# Windows PowerShell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py -OutFile install.py
python install.py D:\Test-Agent
```

### 方法 2：Shell 脚本（Linux / macOS）

```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh
chmod +x install.sh
./install.sh
```

### 方法 3：PowerShell 脚本（Windows）

```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.ps1 -OutFile install.ps1
.\install.ps1
```

### 方法 4：pip 安装

```bash
pip install test-agent
# 或带可选依赖
pip install test-agent[all]
```

### 方法 5：源码安装

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
cd Test-Agent
pip install -e .
# 或使用 install.py 本地模式（自动检测源码目录）
python install.py /path/to/deploy-target
```

> **前置条件：** Python >= 3.10。Git 和 Node.js 缺失时安装脚本自动补装（winget / brew / apt）。
> **安装时长：** 首次约 10-15 分钟（含 pip 依赖 + Playwright Chromium 浏览器）。
> **国内网络：** 自动检测并启用清华 PyPI 镜像加速。

---

## 📝 从 V1.x 升级

1. **备份数据：** 复制 `.env`、`quality_gates.yaml`、`workspace/` 到安全位置。
2. **运行迁移脚本：**
   ```bash
   python scripts/migrate_to_v2.py
   ```
3. **删除旧虚拟环境：**
   ```bash
   rm -rf .venv          # Linux / macOS
   rmdir /s .venv        # Windows
   ```
4. **重新部署：**
   ```bash
   python install.py --update
   ```
5. **验证：**
   ```bash
   tagent doctor                   # 健康检查
   tagent doctor --manifests       # 确认 48/48 manifest 加载
   pytest runtime/tests/ -v        # 确认 238 条测试全绿
   ```

> 轻量更新（保留用户数据和 .venv）：`python install.py --update`

---

## ⚠️ 已知问题

| 问题 | 影响 | 计划 |
|------|------|------|
| Windows 下 scikit-image / scikit-learn / opencv-python 需 C 编译器 | visual-test 技能不可用 | 安装 Visual Studio Build Tools 后手动 `pip install`；下一版提供预编译 wheel |
| Prefect flow 模式下流式输出偶现延迟 | 大规模 DAG 时进度更新滞后 1-2 秒 | 已在 #397 中优化，关注后续版本 |
| Marketplace Web UI 暂不支持 IE 11 | Edge/Chrome/Firefox/Safari 正常 | 不计划支持 |
| Brew formula 首次安装需手动 `brew tap` | macOS 用户需额外一步 | 已提交 homebrew-core，等待审核 |
| `_upstream_outputs` 残余引用在 7 个 agent docstring 中 | 仅注释，不影响功能 | V2.1.0 清理 |

---

## 📊 版本数据

| 指标 | 数值 |
|------|------|
| Agent 数量 | 16（全 production） |
| Skill 数量 | 32（+ 5 个元 Skill 子目录） |
| Utils 模块 | 92（12 子目录） |
| 测试数量 | 238（179 V2 + 59 留存） |
| 测试通过率 | 100%（0 回归） |
| Rust 测试 | 23 |
| CI jobs | 18（3 平台矩阵） |
| 知识图谱节点 | 5,388 |
| 知识图谱边 | 8,902 |
| 质量门禁 | 6（smoke / regression / perf / security / CI / release） |

---

## 🔗 相关链接

- [GitHub 仓库](https://github.com/Wool-xing/Test-Agent)
- [完整 CHANGELOG](CHANGELOG.md)
- [架构设计文档](../02-架构设计/)
- [功能规划文档](../03-功能规划/)
- [Sprint 状态追踪](../SPRINT-STATUS.md)
- [问题反馈](https://github.com/Wool-xing/Test-Agent/issues)
- [贡献指南](https://github.com/Wool-xing/Test-Agent/blob/main/CONTRIBUTING.md)
