# AI 编程助理 — 项目开发约束

> 本文档是 Test-Agent 项目所有 AI 编程助理的强制约束。
> 违反任一条 = 代码不合规，不可提交。

---

## 一、架构硬约束

### 1.1 五层分离，不可跨越

```text
ai/         ← AI模式界面层 (.md only, 不可放.py)
apps/       ← 分发应用层 (自包含, 不可放共享逻辑)
deploy/     ← 部署物料层 (install.py原材料, 不可放源码)
runtime/    ← CLI运行时引擎 (业务逻辑)
utils/      ← 共享工具层 (双模式共用, 不可依赖runtime)

```text

**违反示例：在 `utils/` 里 `from runtime.config import ...`**

### 1.2 依赖方向单向

```text

ai/ ──→ utils/ ←── runtime/ ←── apps/

```text

- `utils/` 是底层，不依赖任何上层模块
- `runtime/` 可依赖 `utils/`，不可被 `utils/` 依赖
- `apps/` 可依赖 `runtime/` + `utils/`，不可反向
- `ai/` 是纯文档，无代码依赖

### 1.3 部署后路径 ≠ 源码路径

| 环境 | agents位置 | skills位置 | config位置 |
| ------ | ----------- | ----------- | ------------ |
| 源码 | `ai/agents/` | `ai/skills/` | `deploy/config/` |
| 部署 | `agents/` | `skills/` | （散落在根目录） |

**所有路径通过 `runtime/config/settings.py` 获取，禁止硬编码。**

---

## 二、路径管理约束

### 2.1 绝对禁止

```python

# ❌ 禁止：硬编码路径

Path(__file__).resolve().parents[2] / "agents"
Path.cwd() / "config" / ".env.example"
"agents/"  # 裸字符串路径

```text

### 2.2 唯一正确方式

```python

# ✅ 正确：通过settings获取

from runtime.config.settings import get_settings
s = get_settings()
s.experts_dir    # ai/agents (源码) → agents (部署, .env覆盖)
s.skills_dir     # ai/skills (源码) → skills (部署, .env覆盖)
s.config_dir     # deploy/config
s.templates_dir  # deploy/config/templates
s.scripts_dir    # utils
s.workspace_dir  # workspace
s.project_root   # 项目根目录

```text

### 2.3 如果要加新目录

1. 在 `runtime/config/settings.py` 加一个 `xxx_dir: Path` 字段
2. 在 `deploy/config/.env.example` 加对应的部署时覆盖（如果部署路径不同）
3. 所有模块通过 `get_settings().xxx_dir` 引用
4.**禁止任何模块自己算路径**

---

## 三、文件放置约束

### 3.1 新文件放哪

| 你要做什么 | 放这里 | 命名规则 |
| ----------- | -------- | --------- |
| 新 Agent 角色 | `ai/agents/NN-名称.md` | 编号递增，中文名 |
| 新 Skill 工作流 | `ai/skills/名称.md` | 小写英文，连字符分隔 |
| 新 CLI 命令 | `runtime/cli/commands/名称.py` | 小写英文，下划线分隔 |
| 新工具函数 | `utils/<子目录>/名称.py` | 按功能选子目录 |
| 新分发应用 | `apps/名称/` | 自包含，独立构建 |
| 新部署模板 | `deploy/config/` | 同步更新 install.py |
| 新合规配置 | `deploy/profiles/名称.yaml` | 标准名称 |
| 新文档 | `docs/` 对应子目录 | 中文或英文 |

### 3.2 根目录只能放什么

```text

✅ 入口文件:   CLAUDE.md, install.py
✅ 项目元信息: README.md, LICENSE, CHANGELOG.md, VERSION, ...
✅ 配置文件:   .gitignore, .editorconfig, pytest.ini, ...
✅ 目录:       ai/, apps/, deploy/, runtime/, utils/, docs/, scripts/, ...

❌ 禁止: 任何功能代码、.md定义、临时文件、构建产物

```text

---

## 四、防污染约束

### 4.1 绝不提交

- `__pycache__/` `*.pyc` `.pytest_cache/` `.ruff_cache/`
- `node_modules/` `package-lock.json` `dist/` `out/` `build/`
- `*.log` `*.bak` `*.tmp` `.coverage`
- `workspace/` 下除 `_demo/` 外的所有内容
- `.env` `.env.local` 任何含密钥的文件
- `.claude/agents/` `.claude/skills/` `.claude/cache/` `.claude/sessions/`

### 4.2 开发前检查

```bash

# 每次提交前确认

git status  # 有没有不该提交的文件？

```text

---

## 五、验证约束

### 5.1 禁止假阳性

-**不信任纯脚本扫描结果**— 脚本说"零引用"不代表真没用
-**不信任mock测试**— 只信任实跑验证
-**不根据文档猜测**— 文档提到某文件不代表代码真用了它

### 5.2 每次改动后必须验证

```bash

# 至少跑这个确认核心没坏

python -c "from runtime.registry.registry import build_catalog; c=build_catalog(); assert len(c.experts)==16; assert len(c.skills)==32; print('OK')"

```text

### 5.3 批量改动前

1. 先用 `grep -rn` 查全局引用
2. 确认影响范围
3. 改一处，测一处
4. 不攒到最后一起测

---

## 六、双模式互不干扰

-**改 AI 模式 (`ai/`)**→ 不影响 CLI 模式 (`runtime/`)
-**改 CLI 模式 (`runtime/`)**→ 不影响 AI 模式 (`ai/`)
-**改 `utils/`**→ 影响双模式，需谨慎
-**改 `deploy/`**→ 只影响 install.py 部署行为，不影响源码运行

---

## 七、实诚自检清单

每次提交前问自己：

1. 有没有硬编码路径？→ 应该全部走 settings
2. 新文件放对目录了吗？→ 对照 3.1
3. 有没有不该提交的文件？→ `git status` 确认
4. 核心功能实测通过了吗？→ 至少 registry catalog 能构建
5. 改 `utils/` 了吗？→ 如果改了，要测双模式都正常
6. 有没有删除任何 .py 源码？→ 如有，必须有充分理由且记录在 commit message

---

>**这些约束的目标：让项目永远不再混乱。**
>**如果AI编程助理不理解某条约束，必须先问，不能跳过。**
