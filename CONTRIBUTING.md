# 贡献指南

欢迎扩展本项目。所有新增 agent / skill / utils 流程统一在此文档。

## 项目架构速览

| 目录 | 用途 | 放什么 | 不放什么 |
| ------ | ------ | -------- | --------- |
| `ai/` | AI模式界面层 | Agent .md, Skill .md | Python代码 |
| `apps/` | 分发应用 | desktop/, mobile/ 等 | 共享业务逻辑 |
| `deploy/` | 部署物料 | 配置模板, 市场, 合规 | 源码 |
| `runtime/` | CLI引擎 | 业务逻辑.py | .md定义 |
| `utils/` | 共享工具 | 工具函数.py | 编排逻辑 |
| `docs/` | 文档 | 知识库, 教程 | 历史快照 |
| `workspace/` | 运行时产出 | 测试报告(全部gitignored) | 源码 |

**核心规则：新增文件前先问——这属于哪一层？**找不到答案就在issue里问。

---

## 添加新 Agent

1. 选定分类（核心通用 9 / 平台扩展 5 / 垂直领域 2）
2. 文件命名 `15-XXX.md`（按编号递增）
3. 创建 `specs/agents/<name>/manifest.yaml`（参考已有 manifest 格式，schema 定义在 `specs/manifest.py`）
4. 编写 system_prompt + output_schema
5.**同步**：
   - 运行 `python scripts/render_manifest.py --name <name>` 生成 AI Mode 用的 .md 文件
   - 更新 `specs/` 对应目录
   - 如 script-backed，添加 `script_path` 指向 utils/
   - `docs/getting-started/部署说明.md` 拷贝清单加

---

## 添加新 Skill

1. 选定分类（通用 8 / 平台专项 5）
2. 文件命名 `<verb>-<noun>.md`（如 `chaos-test.md`）
3. 顶部 YAML frontmatter（可选 `requires_layer: [base, <layer>]` 标注依赖层，值见 `05-install-deploy.md` 六层定义）
4. 必含章节：
   - 🔔 开测前准备清单（平台 skill 必有）
   - 触发方式
   - 适用场景
   - 执行流程
   - 质量门禁
   - 输出文件

5.**同步**：
   - `ai/skills/README.md` 加一行
   - `00-项目导航.md` 加一行
   - `docs/getting-started/使用手册.md` skill 详解段加描述
   - `01-测试主管.md` 快速命令清单加一行
   - `install.py` skills 数组加文件名
   - `docs/getting-started/部署说明.md` 拷贝清单加

---

## 添加新 utils

1. 选定分类（核心 / 平台 / 协议 / 非功能 / 用例方法 / 测试类型 / 安全增强 / DB-契约-API / 移动专项 / a11y-i18n / 度量 / 区块链-AI 对抗 / 报告-SLO-邮件-减重 / 输入加载）
2. 文件名小写下划线（如 `chaos_helper.py`）
3. 顶部 docstring 标注被引用方
4. 必含：公开 API + CLI（argparse）
5.**同步**：
   - `utils/README.md` 表格加一行
   - `00-项目导航.md` 对应分类加一行
   - `deploy/config/requirements.txt` 加新依赖（标 [稳定层]/[可选]/[外部]）
   - `deploy/config/.env.example` 加配置字段
   - `deploy/config/conftest.py` `pytest_configure` 加产出目录
   - `deploy/config/pytest.ini` markers 加新标记
   - `install.py` utils 数组 + 数字
   - `docs/getting-started/部署说明.md` 拷贝清单 + 数字

---

## 添加新 marker

`pytest.ini` markers 段加一行，**必须**：

- 全小写下划线
- 注释说明用途
- 同步到 `00-项目导航.md` 维度表（如适用）

---

## 添加新 .env 字段

1. `deploy/config/.env.example` 加（带注释）
2. `docs/getting-started/配置清单.md` 字段说明加一行
3. `deploy/config/conftest.py` `EnvConfig` 加字段（如功能必需）
4. CI yml / Jenkins Credentials 同步（如 CI 需要）

---

## 提交规范（Conventional Commits）

```text
feat(agent): 加 15-AR测试 专家
fix(utils): jmeter_result_parser 修复 timeStamp 排序
docs(readme): 更新覆盖矩阵
chore(deps): 升级 pytest 7.4.3 → 7.5.0
ci(actions): pip-audit 加 --strict
refactor(skill): smoke-test 改并行 step
test(utils): data_factory 加 cleanup 单测
perf(jmeter): 减少不必要心跳

```text

---

## PR 流程

1. Fork → 新建 feature 分支（`feat/xxx` / `fix/xxx`）
2. 改动 + 同步上述清单
3. 本地跑：
   ```bash
   pytest --collect-only       # 无 ImportError
   ruff check workspace/ utils/
   pip-audit -r requirements.txt --strict
   ```

4. 提 PR → 等 Dependabot / CI 绿灯 → reviewer 审 → merge

---

## 自检脚本（一键验证项目完整性）

```bash

ls ai/agents/[0-9]*.md | wc -l   # 16（或 +N）
ls ai/skills/*.md | grep -v README | wc -l  # 32（或 +N,不含 3 个元 skill 子目录）
ls utils/*.py | wc -l         # 79（或 +N,含__init__.py）
grep -c "^    [a-z_]+:" deploy/config/pytest.ini  # markers 数
python -c "from utils.api_retry_util import call_with_retry; print('OK')"
pytest --collect-only

```text

---

## 联动规则

任一文档/代码改动 → 必须同步到所有引用方，并加 `CHANGELOG.md` 条目。

### 联动改动清单速查

| 改动类型 | 必同步至 |
| --------- | --------- |
| 新增/删除 Agent | `ai/agents/README.md` + `00-项目导航.md` + `docs/getting-started/部署说明.md` 拷贝清单 + `01-测试主管.md` 路由表 + `prd_loader.PLATFORM_KEYWORDS`（install.py 用 glob 自动发现，无需手动加文件名） |
| 新增/删除 Skill | `ai/skills/README.md` + `00-项目导航.md` + `docs/getting-started/使用手册.md` skill 详解 + `01-测试主管.md` 快速命令清单（install.py 用 glob 自动发现） |
| 新增/删除 utils | `utils/README.md` + `00-项目导航.md` + `requirements.txt` + `.env.example` + `conftest.py::pytest_configure` + `pytest.ini` markers（install.py 用 os.walk 自动发现 .py） |
| 数字变化（18/32+3 子目录/49） | grep 全项目 + 同步顶层 README/FULL_GUIDE/00-项目导航/ROADMAP/使用手册/部署说明/install.py + ci.yml `file-count` job 校验 |
| URL/repo 名变化 | grep `Wool-xing/Test-Agent` 全替换 + `install.py::REPO_URL` + `dependabot.yml` |
| 门禁阈值变化 | `utils/ci_quality_gate.py::GATES` + `utils/jmeter_result_parser.py::DEFAULT_GATES_*` + `ai/agents/01-测试主管.md::QUALITY_GATES` + 各 skill 门禁段 |

### 自动化保障

- `pre-commit`：16/32/79 文件统计 + .env 防护 + gitleaks 凭据扫描 + ruff
- `.github/workflows/ci.yml`：16/32/79 自校 + Markdown 链接有效性 + utils 导入
- `.github/workflows/codeql.yml`：python + GitHub Actions 安全扫描

### 提交前自检

```bash

pre-commit run --all-files
pytest --collect-only

```text

---

## RACI 协作矩阵（浓缩版）

> 完整路由逻辑见 `ai/agents/01-测试主管.md` PLATFORM_KEYWORDS 与 `ai/agents/README.md` 流程依赖关系。

### 缩写

-**R**= Responsible（执行者，可多个）
-**A**= Accountable（最终负责，每行只 1 个）
-**C**= Consulted（被咨询）
-**I**= Informed（被通报）
- 空 = 不参与

### 16 专家代号

| 代号 | 专家 | 类别 |
| ------ | ------ | ------ |
| TL | test-lead | 协调者 |
| RA | requirements-analyst | 核心 |
| TD | testcase-designer | 核心 |
| EM | env-manager | 核心 |
| DP | data-preparer | 核心 |
| AE | automation-engineer | 核心 |
| TE | test-executor | 核心 |
| BM | bug-manager | 核心 |
| RG | report-generator | 核心 |
| MT | mobile-tester | 平台扩展 |
| DT | desktop-tester | 平台扩展 |
| VT | visual-tester | 平台扩展 |
| ST | system-tester | 平台扩展 |
| AT | ai-tester | 平台扩展 |
| PT | pentest-tester | 垂直领域 |
| AMT | automotive-tester | 垂直领域 |

### RACI 主表（测试维度 × 专家）

| 测试维度 | TL | RA | TD | EM | DP | AE | TE | BM | RG | MT | DT | VT | ST | AT | PT | AMT |
| --------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ----- |
| 需求分析 | A | R | C | I | I | I | I | I | I | C | C | C | C | C | C | |
| 用例设计-功能 | A | C | R | I | C | I | I | I | I | C | C | C | C | C | C | |
| 用例设计-非功能 | A | C | R | I | C | C | C | C | I |  |  |  |  |  | C | |
| 环境准备 | A | I | I | R | C | C | C | I | I | C | C |  | C |  | C | |
| 数据准备 | A | I | C | C | R | C | C | I | I | C |  |  | C | C | | |
| Web 自动化 | A | I | C | I | C | R | C | I | I |  |  |  |  |  | | |
| API 自动化 | A | I | C | I | C | R | C | I | I |  |  |  | C |  | | |
| 性能（JMeter） | A | C | C | C | C | R | R | I | C |  |  |  |  |  | | |
| 移动端 | A | C | C | C | C | C | C | I | I | R |  |  |  |  | | |
| 桌面端 | A | C | C | C | C | C | C | I | I |  | R |  |  |  | | |
| 视觉/游戏 | A | C | C | C | C | C | C | I | I |  |  | R |  |  | | |
| 系统/IoT/音视频 | A | C | C | C | C | C | C | I | I |  |  |  | R |  | C | C |
| AI/LLM | A | C | C | C | C | C | C | I | I |  |  |  |  | R | C | |
| 安全（SAST/DAST/Fuzz） | A | I | R | C | I | C | C | R | I |  |  |  |  | C | R | |
| 兼容矩阵 | A | I | R | C | I | R | C | I | I | C | C |  |  |  | | C |
| 弱网 | A | I | C | C | I | C | R | I | I | C |  |  |  |  | | |
| 稳定 Soak | A | I | C | C | I | C | R | I | I | C |  |  |  |  | | |
| 可靠性（重试/降级） | A | I | C | C | I | R | C | I | I |  |  |  |  |  | | C |
| 混沌 | A | I | C | C | I | C | R | I | I |  |  |  |  |  | C | |
| 灾备 Failover | A | I | C | R | I | C | R | I | I |  |  |  | C |  | C | C |
| UX 度量 | A | I | R | C | I | R | C | I | C |  |  |  |  |  | | |
| 易用性（Nielsen） | A | I | R | C | I | C | I | I | I |  |  |  |  |  | | |
| 探索性 SBTM | A | I | R | C | C | C | C | C | I |  |  |  |  |  | | |
| Web Vitals | A | I | C | I | I | R | C | I | I |  |  |  |  |  | | |
| A11y 无障碍 | A | I | R | I | I | R | C | I | I |  |  |  |  |  | | |
| i18n / l10n | A | I | R | I | I | R | C | I | I |  |  |  |  |  | | |
| 数据库测试 | A | I | C | C | R | R | C | I | I |  |  |  |  |  | | |
| 契约测试 | A | C | R | I | C | R | C | I | I |  |  |  |  |  | | |
| 视觉回归 | A | I | C | I | I | C | C | I | I |  |  | R |  |  | | |
| AI 对抗/越狱 | A | C | C | I | I | C | C | C | I |  |  |  |  | R | C | |
| 变异测试 | A | I | R | I | I | C | C | I | I |  |  |  |  |  | | |
| DORA / 度量 | A | I | C | I | I | C | R | R | R |  |  |  |  |  | | |
| Bug 提交 BugTracker | A | I | I | I | I | I | C | R | C | I | I | I | I | I | I | I |
| 报告生成 | A | I | I | I | I | I | C | C | R | I | I | I | I | I | I | I |
| 多端通知 | A | I | I | I | I | I | I | I | R | I | I | I | I | I | I | I |
|**上线决策**|**R/A**| C | C | I | I | C | C | C | C | I | I | I | I | I | I | I |

### 责任边界冲突解决

| 冲突场景 | 解决路径 |
| --------- | --------- |
| 同一维度多 R（如安全：TD + BM 都 R） | TD 负责"用例设计与扫描执行"；BM 负责"漏洞分类提交 BugTracker（默认禅道）"。分工明确，不重复 |
| 平台扩展专家发现非自己平台问题 | 走 BM 提交，BM 路由给对应平台专家；不直接跨平台修 |
| TL 与平台专家路由冲突（PRD 含多平台） | TL 编排核心 8 + 路由到的平台专家并行；不强制串行 |
| 决策不一致（如 TE 觉得能上线，TL 觉得不行） | TL 一票决（A 角色定义） |
| 跨专家依赖阻塞 | 阻塞方主动通知 TL；TL 重新调度优先级 |

### 与质量门禁联动

| 门禁层 | A 责任人 | R 执行人 |
| -------- | --------- | --------- |
| smoke ≥95% | TL | TE |
| regression P0=100% / P1≥95% / 总体≥90% | TL | TE |
| 性能 TPS / P95 双模式 | TL | AE + TE |
| 覆盖率 ≥80% | TL | AE |
| Flaky <5% | TL | TE |
| 上线决策 | TL（独有 R+A） | - |
