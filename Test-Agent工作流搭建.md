# 使用 Claude Code 搭建测试全流程专家团队指南 V1.0.0

> **本文件是单文件全嵌入版**，与各分目录（02~06）保持同步。修改任一分目录文件后须回写本文件对应段落。
> 项目目录名：`Test-Agent工作流搭建`（统一名称，不再使用其他别名）
> **快速分类速查**：见根目录 `00-项目导航.md`（按通用流程 / 平台专项 / 协议 / 输入 / CI 五维分类）。
> **子目录索引**：`02-专家定义/README.md` / `03-技能定义/README.md` / `05-代码示例/README.md`。

> **9+5 位专家（核心 9 + 平台扩展 5）/ 13 个执行技能（核心 8 + 平台扩展 5）/ 全链路覆盖（Web/API/移动/桌面/小程序/视觉游戏/IoT/音视频/链路追踪/MQ/AI）/ JMeter 性能（双模式）/ 指数退避 10-20-40s / Flaky 检测 / 覆盖率 ≥80% / CI/CD 双模式分层**

## 核心特点

- **9 + 5 位专家协作**：test-lead 协调 + 8 核心专家 + 5 平台扩展专家（移动 mobile-tester / 桌面 desktop-tester / 视觉 visual-tester / 系统 system-tester / AI ai-tester）
- **13 种执行技能**：核心 8（smoke / test-coordinator / regression / testcase-design / python-script-gen / jmeter-script-gen / data-preparation / zentao-bug-submission）+ 平台扩展 5（mobile-test / desktop-test / visual-test / system-test / ai-test）
- **工程级质量门禁（分层）**：smoke / regression / performance_full / performance_ci_quick
- **指数退避重试**：`utils/api_retry_util.call_with_retry`（base_delay=10, max=60, retries=3 → 10/20/40s）
- **JMeter 性能双模式**：CI 默认 ci_quick（5并发，门禁 TPS≥20），release/手动 full（50并发，TPS≥100）
- **CI/CD 就绪**：GitHub Actions + Jenkins，门禁统一调 `utils/ci_quality_gate.py`
- **MCP 收口**：当前仅启用 filesystem；通知/Bug 走 SDK 直连 webhook，4 个自定义 mcp_server 后续按需实现

---

## 一、快速开始

### GitHub 一键部署（最快）

```bash
# Mac / Linux 一行远程拉起（仓库根 install.sh 自动 clone + 部署）
curl -fsSL https://raw.githubusercontent.com/YOUR-USER/Test-Agent工作流搭建/main/install.sh | bash -s -- /path/to/your-test-project
```

完成后：编辑 `.env` → `claude /login` → `cd 项目目录 && claude` → `> /smoke-test`。

详见 `01-快速开始/使用手册.md` "🚀 启动指引"。

### 3 步搭建（手动）

**步骤 1：创建目录结构**

```bash
# Linux/Mac
mkdir -p your-test-project
cd your-test-project
mkdir -p .claude/{agents,skills}
mkdir -p .github/workflows
mkdir -p utils src
mkdir -p workspace/{测试计划,需求分析,测试用例,测试数据}
mkdir -p workspace/自动化脚本/python/{pages,api,tests,scripts}
mkdir -p workspace/自动化脚本/jmeter
mkdir -p workspace/执行日志/{allure-results,jmeter-results,jmeter-report,coverage-report,baselines,history,截图,报告}
```

```powershell
# Windows PowerShell（拆开 New-Item，不依赖 brace expansion）
$dirs = @(
    ".claude\agents", ".claude\skills",
    ".github\workflows", "utils", "src",
    "workspace\测试计划", "workspace\需求分析", "workspace\测试用例", "workspace\测试数据",
    "workspace\自动化脚本\python\pages", "workspace\自动化脚本\python\api",
    "workspace\自动化脚本\python\tests", "workspace\自动化脚本\python\scripts",
    "workspace\自动化脚本\jmeter",
    "workspace\执行日志\allure-results", "workspace\执行日志\jmeter-results",
    "workspace\执行日志\jmeter-report", "workspace\执行日志\coverage-report",
    "workspace\执行日志\baselines", "workspace\执行日志\history",
    "workspace\执行日志\截图", "workspace\执行日志\报告"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
```

**步骤 2：创建配置文件**（详见第三节）

**步骤 3：启动 Claude Code 并使用斜杠技能**

```bash
claude
```

在 Claude Code 提示符（`>` 后是输入，**不是 shell 命令**）：

```
> /smoke-test            ← 10 分钟 P0 冒烟（11min 上限，含缓冲）
> /test-coordinator      ← 完整流程（含 JMeter 性能）
> /regression-test       ← 回归（git diff + Flaky + JMeter）
> /testcase-design       ← 仅生成 4 Sheet 测试用例 Excel
> /python-script-gen     ← pytest UI/API 脚本
> /jmeter-script-gen     ← JMeter JMX 脚本
> /data-preparation      ← 测试数据 + JMeter CSV
> /zentao-bug-submission ← 禅道 Bug 规范提交
```

> 完整跨平台部署（含 Java/JMeter/Allure CLI）见 `01-快速开始/部署说明.md`。

---

## 二、专家定义（.claude/agents/）

### 2.1 测试主管（test-lead）

```markdown
---
name: test-lead
description: 测试主管 - 协调 8 位专家完成完整测试流程。test-lead 自身是协调者，不计入被协调清单。
tools: Read, Write, Bash, Grep, Glob
---

你是一位拥有 15 年经验的测试技术总监。

## 协调的 8 位专家

| 序号 | 专家 | 职责 |
|------|------|------|
| 1 | requirements-analyst | 需求分析与测试范围 |
| 2 | testcase-designer | 用例设计 |
| 3 | env-manager | 环境准备与健康检查 |
| 4 | data-preparer | 数据准备与脱敏 |
| 5 | automation-engineer | 自动化脚本编写 |
| 6 | test-executor | 测试执行与监控 |
| 7 | bug-manager | Bug 提交与追踪 |
| 8 | report-generator | 报告生成与通知 |

## 工作流程（含并行优化）

```
1. requirements-analyst
2. testcase-designer
3. [并行预备] env-manager（基础 connectivity 通过后）→ data-preparer
4. automation-engineer（pytest + /jmeter-script-gen → JMX）
5. /smoke-test 子技能（门禁 P0≥95%）
6. test-executor 功能回归（P0+P1，含 cov）
7. test-executor JMeter 性能（ci_quick / full 模式）
8. bug-manager
9. report-generator
```

## 质量门禁（分层）

\```python
QUALITY_GATES = {
    "smoke": {
        "p0_pass_rate": 95,
        "p0_bug_count": 0,
        "api_response_ms": 3000,
    },
    "regression": {
        "p0_pass_rate": 100,
        "p1_pass_rate": 95,
        "total_pass_rate": 90,
        "coverage": 80,           # cov 指向 $APP_SRC_PATH
        "flaky_rate": 5,
        "new_p0_bugs": 0,
    },
    "performance_full": {         # 手动/release 触发
        "tps_min": 100,
        "p95_max_ms": 500,
        "avg_max_ms": 200,
        "error_rate_max_pct": 1.0,
        "regression_max_pct": 20,
    },
    "performance_ci_quick": {     # CI 默认
        "tps_min": 20,
        "p95_max_ms": 800,
        "avg_max_ms": 400,
        "error_rate_max_pct": 1.0,
    },
}
\```

## 性能基线管理

- 路径：`workspace/执行日志/baselines/perf_baseline.json`
- 更新规则：仅 release 分支 + full 模式 + 当次门禁全 PASS 时执行 `python -m utils.jmeter_result_parser ... --update-baseline`

## 经验原则

1. 质量不妥协：smoke<95% 或 P0 Bug 未修复坚决不放行
2. 数据驱动：决策基于测试数据
3. 左移思维：需求评审阶段介入
4. 风险可视化
```

### 2.2 需求分析（requirements-analyst）

```markdown
---
name: requirements-analyst
description: 需求分析专家 - 输出 Markdown 详细报告 + JSON 摘要（供下游 agent 解析）
tools: Read, Write, Grep, Glob
---

## 双轨输出

- `workspace/需求分析/requirements_analysis_{YYYYMMDD}.md`
- `workspace/需求分析/requirements_summary_{YYYYMMDD}.json`

## JSON 摘要 Schema

\```json
{
  "version": "v1.0.0",
  "in_scope": [{"feature": "登录", "priority": "P0", "modules": ["login"]}],
  "out_of_scope": [{"feature": "...", "reason": "..."}],
  "business_rules": [{"id": "BR-001", "description": "...", "verification": "..."}],
  "risks": [{"level": "high", "area": "...", "impact": "...", "mitigation": "..."}],
  "data_requirements": [{"type": "normal_user", "count": 3, "constraints": {}}],
  "performance_requirements": {"tps_min": 100, "p95_max_ms": 500, "concurrent_users": 50}
}
\```
```

### 2.3 用例设计（testcase-designer）

```markdown
---
name: testcase-designer
description: 用例设计专家 - 输出 4 Sheet Excel（用例总览 / 测试用例 / P0冒烟集 / P0+P1回归集）
tools: Read, Write, Grep, Glob
---

## 优先级占比（合计 100%）

| 优先级 | 占比 | 标准 |
|--------|------|------|
| P0 | 10% | 核心业务路径 |
| P1 | 30% | 主要功能 |
| P2 | 40% | 次要功能 |
| P3 | 20% | 边缘场景 |

## 用例 ID 规范

`TC-{MODULE}-{TYPE}-{NUM}`，TYPE ∈ {UI, API, PERF, SEC}

示例：`TC-LOGIN-UI-001`、`TC-PAYMENT-API-003`、`TC-LOGIN-PERF-001`

## Excel 由 utils/excel_generator.create_testcase_excel 生成（4 Sheet 标准）

落盘：`workspace/测试用例/testcases_[模块]_[YYYYMMDD].xlsx`
```

### 2.4 环境管理（env-manager）

```markdown
---
name: env-manager
description: 环境管理专家 - test/staging 多环境（prod 直接 raise 禁用）+ Docker 支持
tools: Read, Write, Bash, Grep, Glob
---

## EnvConfig 唯一权威在 conftest.py

env-manager 不再单独维护 EnvConfig 副本，避免双源漂移。
通过 `from conftest import get_current_env` 调用。

## 健康检查脚本（独立 .sh 文件）

放置 `workspace/自动化脚本/python/scripts/health_check.sh`（见 04-环境管理.md 完整脚本）。

## docker-compose.test.yml（wiremock 锁定 3.3.1）

\```yaml
services:
  test-db:
    image: postgres:14-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
  test-redis:
    image: redis:7-alpine
  mock-server:
    image: wiremock/wiremock:3.3.1
    ports:
      - "8080:8080"
\```

## 异常处理：指数退避 10/20/40s（与全栈对齐）
```

### 2.5 数据准备（data-preparer）

```markdown
---
name: data-preparer
description: 数据准备专家 - 全部委托 utils/data_factory / data_masking / jmeter_csv_exporter
tools: Read, Write, Bash, Grep, Glob
---

## 调用方式

\```python
from data_factory import UserFactory, OrderFactory, TestDataManager, LOGIN_TEST_DATA
from data_masking import DataMasker
from jmeter_csv_exporter import generate_jmeter_dataset

# 数据生成
mgr = TestDataManager(env_config)
user = mgr.create_test_user(role="admin")

# 落盘到权威路径（conftest fixture 直接消费）
import json
from pathlib import Path
out = Path("workspace/测试数据/test_data.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"normal_user": user}, ensure_ascii=False, indent=2))

# JMeter CSV
generate_jmeter_dataset(count=50, output_path="workspace/测试数据/jmeter_users.csv")

# 日志脱敏
masked = DataMasker.mask_dict(user)
\```
```

### 2.6 自动化脚本（automation-engineer）

```markdown
---
name: automation-engineer
description: 自动化脚本专家 - Playwright（UI）+ requests（API）+ JMeter（性能主，通过 /jmeter-script-gen）+ Locust（开发期备）
tools: Read, Write, Edit, Bash, Grep, Glob
---

## 项目结构（部署后）

\```
project_root/
├── conftest.py            # 项目根唯一 conftest（项目内 workspace/自动化脚本/python/ 不再放 conftest）
├── pytest.ini
├── utils/                 # 12 个 .py + __init__.py
├── src/                   # 被测系统源码（cov 指向）
└── workspace/
    └── 自动化脚本/
        ├── python/{pages,api,tests/{test_p0_smoke,test_p1_regression,test_p2_full},scripts}/
        └── jmeter/test_plan.jmx
\```

## API setup fixture 改 class scope

\```python
@pytest.fixture(scope="class")
def user_api(api_client, env_config):
    return UserAPI(api_client, env_config.api_base_url)
\```

## 性能双轨

- **主**：JMeter（通过 /jmeter-script-gen 生成 JMX，CI/release 门禁权威）
- **备**：Locust（`tests/performance/locustfile.py`，开发期 Python 内压测，不参与正式门禁）

## marker 多重要求

`@p0/@p1/@p2/@p3` + `@smoke/@regression/@performance/@security` + `@api/@ui` + `@{module}`
```

### 2.7 测试执行（test-executor）

```markdown
---
name: test-executor
description: 测试执行专家 - 四阶段执行（含 JMeter 性能阶段）
tools: Read, Write, Bash, Grep, Glob
---

## 四阶段模型

\```
阶段1：冒烟（10min）        P0，门禁 ≥95%（不开 reruns）
阶段2：核心回归（30-60min） P0+P1，开 reruns，cov 指向 $APP_SRC_PATH
阶段3：全量测试（按需）     全用例
阶段4：JMeter 性能          ci_quick（CI 默认）/ full（release/手动）
\```

## JMeter 双模式命令

\```bash
PERF_MODE="${PERF_MODE:-ci_quick}"
if [ "$PERF_MODE" = "full" ]; then THREADS=50; RAMPUP=60; DURATION=300; else THREADS=5; RAMPUP=10; DURATION=60; fi

jmeter -n \
    -t workspace/自动化脚本/jmeter/test_plan.jmx \
    -l workspace/执行日志/jmeter-results/result.jtl \
    -e -o workspace/执行日志/jmeter-report/ \
    -Jtarget_host="${TARGET_HOST}" \
    -Jtarget_protocol="${TARGET_PROTOCOL:-http}" \
    -Jtarget_port="${TARGET_PORT:-80}" \
    -Jthreads=${THREADS} -Jrampup=${RAMPUP} -Jduration=${DURATION}

# 解析 + 门禁（含基线对比）
python -m utils.jmeter_result_parser \
    workspace/执行日志/jmeter-results/result.jtl \
    --mode "${PERF_MODE}" \
    --baseline workspace/执行日志/baselines/perf_baseline.json
\```

> TARGET_HOST 不含协议前缀（从 TEST_API_URL 解析 host/protocol/port）。

## 失败分类（落地 JSON）

product_bug / environment_issue / test_code_bug / flaky_test / data_issue
→ 写入 `workspace/执行日志/failure_classification.json`，bug-manager 自动消费。

## Flaky 归档（与 utils/flaky_detector 协作）

\```bash
python -m utils.flaky_detector \
    --archive workspace/执行日志/regression-results.xml \
    --history workspace/执行日志/history --limit 5
\```
```

### 2.8 Bug 管理（bug-manager）

```markdown
---
name: bug-manager
description: Bug 管理专家 - 通过 utils/zentao_bug_manager 提交（severity 1=P0..4=P3 权威）
tools: Read, Write, Bash, Grep, Glob
---

## 优先级 → severity / pri 映射

| 级别 | severity | pri | 修复时间 |
|------|----------|-----|---------|
| P0 | 1 | 1 | 当天 |
| P1 | 2 | 2 | 24 小时内 |
| P2 | 3 | 3 | 3 个工作日 |
| P3 | 4 | 4 | 下版本 |

## 单条提交

\```python
from utils.zentao_bug_manager import ZentaoBugManager, SEVERITY_MAP, PRI_MAP

manager = ZentaoBugManager()
bug = manager.create_bug({
    "title": "登录模块-...",
    "product": 1,
    "severity": SEVERITY_MAP["P0"],
    "pri":      PRI_MAP["P0"],
    "steps": "...",
    "buildFound": "v1.0.0-rc1",
})
\```

## Bug 验证清单（关键修正）

- ✅ 原 Bug 场景完全修复（不再可重现）
- ✅ 修复在生产/预发环境**验证无重现**（语义已修正，原版"可重现"是错的）
- ✅ 修复方式未引入新 Bug
- ✅ 关联功能正常
```

### 2.9 报告生成（report-generator）

```markdown
---
name: report-generator
description: 报告生成专家 - Word + Allure + JMeter HTML + 三端通知（curl 直连）
tools: Read, Write, Bash, Grep, Glob
---

## 全部委托 utils/generate_report.py

\```python
from utils.generate_report import generate_test_report, send_all_notifications

generate_test_report(data, "workspace/执行日志/报告/测试报告_20260510.docx")

# 三端通知（自动跳过未配置的 webhook）
send_all_notifications({
    "project": "...", "environment": "test", "verdict": "通过",
    "pass_rate": 0.967, "p0_bugs": 0, "report_url": "...",
    "perf_tps": 102.5, "perf_p95": 380,
})
\```

## 飞书卡片合法颜色

`turquoise/red/blue/wathet/green/yellow/orange/carmine/violet/purple/indigo/grey`

## 字体 fallback

`["微软雅黑", "PingFang SC", "Noto Sans CJK SC"]`（跨平台）
```

---

## 三、技能定义（.claude/skills/）

> 共 8 个 skill。详细完整内容见 `03-技能定义/` 各文件。下面是关键字段速览。

### 3.1 `/smoke-test`

```markdown
门禁：P0 通过率 ≥95% 且 无新增 P0 Bug；阶段 1+1+1+5+2+1=11min（含 1min 缓冲）
不开 reruns（保留 flaky 信号供 utils/flaky_detector 离线检测）
执行：pytest -m "p0" -n 2 --timeout=60
门禁：python -m utils.ci_quality_gate --smoke-xml ... --output-json ...
```

### 3.2 `/test-coordinator`

```markdown
流程：
needs ↓
requirements-analyst ↓ MD + JSON
testcase-designer ↓ Excel 4 Sheet
env-manager ↓（基础 connectivity 通过后）
data-preparer ↓ test_data.json + jmeter_users.csv
automation-engineer ↓ pytest + /jmeter-script-gen → JMX
/smoke-test ↓ 门禁
test-executor 功能回归 ↓
test-executor JMeter（PERF_MODE=ci_quick / full） ↓
bug-manager ↓
report-generator ↓
test-lead 最终决策

输出文件清单：见 03-技能定义/test-coordinator.md
```

### 3.3 `/regression-test`

```markdown
变更影响：utils.regression_scope（读 workspace/regression_modules.yaml 配置化）
阈值：MAX_AFFECTED_MODULES_FULL_REGRESSION（.env，默认 3）
Flaky：utils.flaky_detector（archive 后离线检测 + history 归档）
JMeter：双模式（ci_quick / full） + 基线对比
cov 指向 $APP_SRC_PATH

reruns vs flaky：
- 冒烟阶段不开 reruns（保留 flaky 信号）
- 回归阶段开 reruns（快速反馈），flaky 由 history 离线检测
```

### 3.4 `/jmeter-script-gen`

```markdown
关键变量（不含协议前缀）：
- target_host：${__P(target_host,test-api.example.com)}
- target_protocol：${__P(target_protocol,http)}
- target_port：${__P(target_port,80)}
- threads / rampup / duration

JMeter 5.x 用 JSONPostProcessor（旧名 JSONPathExtractor 已弃用）
登录失败时 If Controller 中止后续请求（防 401 雪崩）
ResponseAssertion 的 stringProp 必须含 name 属性
模板B 阶梯加压用 3 个串行 ThreadGroup（10→50→100，delay 控制）
```

### 3.5~3.8 其他技能

```
/testcase-design       - 4 Sheet Excel，用例 ID 含 TYPE
/python-script-gen     - pytest UI/API（性能转交 /jmeter-script-gen）
/data-preparation      - row[5] 正确指向"前置条件"，regex 提取并发数
/zentao-bug-submission - SEVERITY_MAP 1=P0；批量提交从 regression_summary.json 消费
```

---

## 四、配置文件

### 4.1 `conftest.py`（项目根唯一权威）

```python
"""pytest 全局配置 - 放置于项目根目录"""
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# 注入 utils 包到 sys.path
_PROJECT_ROOT = Path(__file__).parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@dataclass
class EnvConfig:
    env_name: str
    app_base_url: str
    api_base_url: str
    db_host: str
    db_port: int = 5432
    db_name: str = "testdb"
    db_user: str = "testuser"
    db_password: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    zentao_url: str = ""
    mock_server_url: str = ""


def get_current_env() -> EnvConfig:
    """test/staging 多环境，prod 直接 raise"""
    env = os.getenv("TEST_ENV", "test").lower()
    if env == "prod":
        raise ValueError("禁止以 prod 作为测试环境")
    if env == "test":
        return EnvConfig(
            env_name="test",
            app_base_url=os.getenv("TEST_APP_URL", "http://test.example.com"),
            api_base_url=os.getenv("TEST_API_URL", "http://test-api.example.com"),
            db_host=os.getenv("TEST_DB_HOST", "localhost"),
            db_port=int(os.getenv("TEST_DB_PORT", "5432")),
            db_name=os.getenv("TEST_DB_NAME", "testdb"),
            db_user=os.getenv("TEST_DB_USER", "testuser"),
            db_password=os.getenv("TEST_DB_PASSWORD", ""),
            redis_host=os.getenv("TEST_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("TEST_REDIS_PORT", "6379")),
            zentao_url=os.getenv("TEST_ZENTAO_URL", os.getenv("ZENTAO_BASE_URL", "")),
            mock_server_url=os.getenv("MOCK_SERVER_URL", ""),
        )
    if env == "staging":
        return EnvConfig(
            env_name="staging",
            app_base_url=os.getenv("STAGING_APP_URL", ""),
            api_base_url=os.getenv("STAGING_API_URL", ""),
            db_host=os.getenv("STAGING_DB_HOST", ""),
            db_port=int(os.getenv("STAGING_DB_PORT", "5432")),
            db_name=os.getenv("STAGING_DB_NAME", "stagingdb"),
            db_user=os.getenv("STAGING_DB_USER", "staginguser"),
            db_password=os.getenv("STAGING_DB_PASSWORD", ""),
            redis_host=os.getenv("STAGING_REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("STAGING_REDIS_PORT", "6379")),
            zentao_url=os.getenv("STAGING_ZENTAO_URL", os.getenv("ZENTAO_BASE_URL", "")),
            mock_server_url=os.getenv("MOCK_SERVER_URL", ""),
        )
    raise ValueError(f"未知的测试环境: {env}，可选值: test/staging")


@pytest.fixture(scope="session")
def env_config():
    return get_current_env()


@pytest.fixture(scope="session")
def test_data(env_config):
    """会话级测试数据。路径权威：workspace/测试数据/test_data.json"""
    data_file = Path("workspace/测试数据/test_data.json")
    if data_file.exists():
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)

    try:
        from data_factory import TestDataManager
        mgr = TestDataManager(env_config)
        data = {
            "normal_user": mgr.create_test_user(status="active"),
            "admin_user":  mgr.create_test_user(status="active", role="admin"),
            "locked_user": mgr.create_test_user(status="locked"),
        }
    except Exception as e:
        logger.warning(f"data_factory 不可用，回退兜底: {e}")
        data = {
            "normal_user": {
                "username": os.getenv("TEST_USER", "testuser@example.com"),
                "password": os.getenv("TEST_PASS", "Test@123456"),
            },
            "admin_user": {
                "username": os.getenv("ADMIN_USER", "admin@example.com"),
                "password": os.getenv("ADMIN_PASS", "Admin@123456"),
            },
        }

    data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


@pytest.fixture(scope="session")
def browser_context(env_config):
    """playwright lazy import（避免纯 API 测试加载）"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            base_url=env_config.app_base_url,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN", timezone_id="Asia/Shanghai",
        )
        context.set_default_timeout(30000)
        yield context
        context.close()
        browser.close()


@pytest.fixture(scope="function")
def page(browser_context):
    p = browser_context.new_page()
    yield p
    p.close()


@pytest.fixture(scope="session")
def api_client(env_config):
    """urllib3 Retry 1s/2s/4s。Content-Type 不在 session 默认（按 per-request）"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.base_url = env_config.api_base_url
    session.headers.update({
        "Accept": "application/json",
        "X-Test-Session": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    })
    return session


@pytest.fixture(scope="function", autouse=True)
def cleanup_tracker():
    cleanup_tasks = []
    def register(func, *args, **kwargs):
        cleanup_tasks.append((func, args, kwargs))
    yield register
    for func, args, kwargs in reversed(cleanup_tasks):
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"清理任务失败: {e}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """失败时截图（含 setup/teardown）"""
    outcome = yield
    rep = outcome.get_result()
    if rep.failed and rep.when in ("setup", "call", "teardown") and "page" in item.fixturenames:
        try:
            page = item.funcargs.get("page")
            if page:
                d = Path("workspace/执行日志/截图")
                d.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(d / f"{item.name}_{rep.when}_{datetime.now():%H%M%S}.png"))
        except Exception:
            pass


def pytest_configure(config):
    """启动时创建所有 workflow 产出目录"""
    dirs = [
        "workspace/测试计划", "workspace/需求分析", "workspace/测试用例", "workspace/测试数据",
        "workspace/自动化脚本/python", "workspace/自动化脚本/jmeter",
        "workspace/执行日志/allure-results", "workspace/执行日志/截图",
        "workspace/执行日志/jmeter-results", "workspace/执行日志/jmeter-report",
        "workspace/执行日志/coverage-report", "workspace/执行日志/baselines",
        "workspace/执行日志/history", "workspace/执行日志/报告",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
```

### 4.2 `pytest.ini`

```ini
[pytest]
testpaths = workspace/自动化脚本/python

markers =
    p0: P0级核心用例
    p1: P1级重要用例
    p2: P2级次要用例
    p3: P3级体验优化
    smoke: 冒烟用例
    regression: 回归用例
    performance: 性能用例
    security: 安全用例
    flaky: Flaky 用例（隔离，不计门禁）
    api: API 测试
    ui: UI 测试
    login: 登录模块
    payment: 支付模块
    order: 订单模块
    profile: 用户资料模块
    register: 注册模块

timeout = 120
timeout_method = thread

addopts =
    -v
    --tb=short
    --strict-markers
    -p no:warnings
    --alluredir=workspace/执行日志/allure-results
    --junitxml=workspace/执行日志/junit-results.xml

junit_family = xunit2

# reruns / cov 默认关闭。CI 命令行显式开启：
# --reruns=2 --reruns-delay=5 --cov=$APP_SRC_PATH --cov-report=xml --cov-fail-under=80

log_cli = true
log_cli_level = INFO
log_file = workspace/执行日志/pytest.log
log_file_level = DEBUG

python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
```

### 4.3 `.env.example`（关键字段）

```bash
TEST_ENV=test                 # test | staging（prod 直接 raise）

# 应用
TEST_APP_URL=http://test.example.com
TEST_API_URL=http://test-api.example.com
STAGING_APP_URL=
STAGING_API_URL=

# 数据库（test + staging 全套）
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=testdb
TEST_DB_USER=testuser
TEST_DB_PASSWORD=
STAGING_DB_HOST=
STAGING_DB_PORT=5432
STAGING_DB_PASSWORD=

# Redis
TEST_REDIS_HOST=localhost
TEST_REDIS_PORT=6379
STAGING_REDIS_HOST=
STAGING_REDIS_PORT=6379

# Mock
MOCK_SERVER_URL=http://localhost:8080

# 测试账号
TEST_USER=testuser@example.com
TEST_PASS=Test@123456
ADMIN_USER=admin@example.com
ADMIN_PASS=Admin@123456

# 性能压测账号
PERF_TEST_USER=perf_user
PERF_TEST_PASS=PerfTest@123456

# 禅道（按环境隔离）
ZENTAO_BASE_URL=http://your-zentao.com/zentao/api.php/v1
TEST_ZENTAO_URL=
STAGING_ZENTAO_URL=
ZENTAO_ACCOUNT=
ZENTAO_PASSWORD=

# 通知 webhook（curl 直连，无 MCP 通道）
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 执行配置
HEADLESS=true
PARALLEL_WORKERS=4
TEST_TIMEOUT=120
COVERAGE_THRESHOLD=80

# 性能模式：full（50并发） / ci_quick（5并发）
PERF_MODE=ci_quick
PERF_REGRESSION_MAX_PCT=20

# 回归
MAX_AFFECTED_MODULES_FULL_REGRESSION=3

# 被测系统源码（pytest-cov 指向）
APP_SRC_PATH=./src

LOG_LEVEL=INFO
```

> 注：`ANTHROPIC_API_KEY` 由 Claude Code 通过 `claude /login` 配置，**不写入 .env**。

### 4.4 `.mcp.json`（MCP 收口：仅 filesystem）

```json
{
  "_comment": "MCP 服务配置。当前仅启用 filesystem。zentao/wechat/feishu/dingtalk 通知与 Bug 提交目前走 SDK/curl 直连。如需启用 MCP 通道，自行实现对应 mcp_server 模块后追加配置。",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${PROJECT_ROOT:-./workspace}"],
      "description": "文件系统访问"
    }
  }
}
```

### 4.5 `requirements.txt`

```
# 测试框架核心
pytest==7.4.3
pytest-xdist==3.5.0
pytest-rerunfailures==13.0
pytest-timeout==2.2.0
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-playwright==0.4.4
allure-pytest==2.13.2

# UI/API
playwright==1.40.0
requests==2.31.0

# 性能（主：JMeter 外部安装；备：Locust）
locust==2.25.0

# 数据工厂
faker==20.1.0
factory-boy==3.3.0

# 数据库
psycopg2-binary==2.9.9
pymysql==1.1.0
SQLAlchemy==2.0.25

# 配置/Excel/文档
PyYAML==6.0.1
openpyxl==3.1.2
python-docx==1.1.0

# 工具
python-dotenv==1.0.0
tenacity==8.2.3
loguru==0.7.2

# 外部工具（独立安装，见 01-快速开始/部署说明.md）：
# - JMeter 5.6.3（需 Java 8+）
# - Allure CLI 2.27+（需 Java）
```

---

## 五、核心工具代码（utils/）

> 完整实现见 `05-代码示例/`。下面是关键 API 速览。

### 5.1 `utils/api_retry_util.py` - 指数退避 10/20/40s

```python
def call_with_retry(
    func, *args,
    max_retries: int = 3,
    base_delay: float = 10.0,
    max_delay: float = 60.0,
    retryable_exceptions=(Exception,),
    retryable_status_codes=(429, 500, 502, 503, 504),
    **kwargs,
):
    """
    通用重试包装器。
    第1次失败 → 等10s
    第2次失败 → 等20s
    第3次失败 → 等40s
    Retry-After 兼容秒数 + HTTP-date。
    """
```

### 5.2 `utils/zentao_bug_manager.py` - 禅道 SDK

```python
from utils.zentao_bug_manager import ZentaoBugManager, SEVERITY_MAP, PRI_MAP
# SEVERITY_MAP = {"P0":1,"P1":2,"P2":3,"P3":4}（权威）

manager = ZentaoBugManager()  # 自动从 .env 读取，401 自动续期 token

bug = manager.create_bug({
    "title": "...", "product": 1,
    "severity": SEVERITY_MAP["P0"],
    "pri":      PRI_MAP["P0"],
    "steps": "...",
})

# 批量从 test-executor 输出 JSON 消费
results = manager.batch_submit_from_failures(failures, product_id=1, build_version="v1.0")
```

### 5.3 `utils/data_factory.py` - 数据工厂

```python
from utils.data_factory import UserFactory, OrderFactory, TestDataManager, LOGIN_TEST_DATA

mgr = TestDataManager(env_config)
mgr.create_test_user(role="admin")
mgr.create_batch_users(count=10)
mgr.create_boundary_data("email")  # 含 expected_valid 标注
mgr.cleanup()                       # 反向逐条清理
```

### 5.4 `utils/jmeter_result_parser.py` - JMeter 解析 + 门禁

```python
from utils.jmeter_result_parser import parse_jtl, check_performance_gates, compare_with_baseline

metrics = parse_jtl("workspace/执行日志/jmeter-results/result.jtl")
# duration 用 max(timestamps)（防多线程时序错乱）
# error_rate_pct 单位百分比

result = check_performance_gates(metrics, gates=DEFAULT_GATES_CI_QUICK)  # 或 DEFAULT_GATES_FULL
baseline_cmp = compare_with_baseline(metrics, "...baselines/perf_baseline.json", regression_max_pct=20)
```

CLI：
```bash
python -m utils.jmeter_result_parser <jtl> --mode ci_quick|full --baseline ... --update-baseline
```

### 5.5 其他 utils

```
utils/excel_generator.py        - 4 Sheet Excel（用例总览/详细/P0/P0+P1回归）
utils/data_masking.py           - DataMasker.mask_dict 递归脱敏
utils/jmeter_csv_exporter.py    - CSV 导出 + generate_jmeter_dataset
utils/regression_scope.py       - git diff + regression_modules.yaml 配置化
utils/flaky_detector.py         - junit-xml 历史归档检测
utils/generate_report.py        - Word + 三端通知（curl 直连）
utils/ci_quality_gate.py        - 统一 CI 门禁（消除内联重复）
```

---

## 六、CI/CD 集成

### 6.1 GitHub Actions（`.github/workflows/test.yml`）

要点：

```yaml
on:
  push: { branches: [main, develop, release/*] }
  pull_request: { branches: [main, develop] }
  workflow_dispatch:
    inputs:
      test_level:  { type: choice, options: [smoke, regression, full] }
      perf_mode:   { type: choice, options: [ci_quick, full] }

env:
  PERF_MODE: ${{ github.event.inputs.perf_mode || (startsWith(github.ref, 'refs/heads/release/') && 'full' || 'ci_quick') }}
  APP_SRC_PATH: ${{ secrets.APP_SRC_PATH || './src' }}

jobs:
  preflight:    # 检测 secrets，输出 outputs 供后续 if 引用（解决 secrets 不能直接 if 判断）
  code-quality:
  smoke-test:
  regression-test:    # cov 指向 $APP_SRC_PATH，门禁调 utils/ci_quality_gate
  performance-test:   # 解析 TEST_API_URL → host/protocol/port；JMeter download 含 archive 兜底；调 utils/jmeter_result_parser
  publish-report:
  quality-gate:       # 综合门禁 + 通知（curl 直连 webhook）
```

完整文件见 `06-CICD集成/github-actions-test.yml`。

### 6.2 Jenkins Pipeline（`Jenkinsfile`）

要点：

```groovy
pipeline {
    agent { docker { image 'python:3.11' } }   // 不用 slim
    parameters {
        choice(name: 'PERF_MODE', choices: ['ci_quick', 'full'])
    }
    stages {
        stage('准备')   { /* mkdir 拆开（不依赖 brace expansion）*/ }
        stage('冒烟')   { /* python -m utils.ci_quality_gate */ }
        stage('回归')   { parallel { stage('API回归') { /* -m "(p0 or p1) and api" */ }
                                       stage('UI 回归') { /* -m "(p0 or p1) and ui" */ } } }
        stage('性能')   {
            steps {
                script {
                    def jmeterHome = "/opt/apache-jmeter-5.6.3"
                    sh """ /* 装 JMeter（含 archive 兜底） */ """
                    withEnv(["PATH+JMETER=${jmeterHome}/bin"]) {
                        // PATH 持久跨 sh 块
                        sh "python -m utils.jmeter_csv_exporter --count 50 --output ..."
                        sh "jmeter -n -t ... -Jtarget_host=... -Jtarget_protocol=... -Jtarget_port=..."
                        sh "python -m utils.jmeter_result_parser ..."
                    }
                }
            }
        }
    }
    post {
        always {
            // ant pattern 拆开（不支持 brace expansion）
            archiveArtifacts artifacts: 'workspace/执行日志/**/*.xml,workspace/执行日志/**/*.log,workspace/执行日志/**/*.png,workspace/执行日志/**/*.json',
                             allowEmptyArchive: true
        }
    }
}
```

完整文件见 `06-CICD集成/jenkins-pipeline.groovy`。

stage flag：用 `env.STAGE_X_OK = 'true'`（不依赖不可靠的 `currentBuild.currentResult`）。

---

## 七、质量标准总览

### 功能质量门禁

| 指标 | 冒烟 | 回归 | 不达标处置 |
|------|------|------|---------|
| P0 通过率 | ≥95% | 100% | 停止 / 等待修复 |
| P1 通过率 | - | ≥95% | 记录遗留风险 |
| 整体通过率 | - | ≥90% | 评估风险 |
| 代码覆盖率（$APP_SRC_PATH） | - | ≥80% | 补充用例 |
| 新增 P0 Bug | 0 | 0 | 阻断发布 |
| Flaky 比例 | - | <5% | 隔离 + 分析 |

### 性能质量门禁（双模式）

| 指标 | full（50并发） | ci_quick（5并发） |
|------|--------------|------------------|
| TPS | ≥100 | ≥20 |
| P95 响应 | ≤500ms | ≤800ms |
| 平均响应 | ≤200ms | ≤400ms |
| 错误率 (pct) | <1% | <1% |
| 基线回归 | <20% | 不强制 |

### 技术栈对照

| 类型 | 工具 | 版本 |
|------|------|------|
| UI | Playwright | 1.40.0 |
| API | requests + pytest | 2.31.0 / 7.4.3 |
| 性能（主） | Apache JMeter | 5.6.3（独立装 Java） |
| 性能（备） | locust | 2.25.0 |
| 数据 | faker + factory-boy | 20.1.0 + 3.3.0 |
| 覆盖率 | pytest-cov | 4.1.0 |
| 并行 | pytest-xdist | 3.5.0 |
| 重试（封装） | tenacity / 自实现 10/20/40s | 8.2.3 |
| Excel | openpyxl | 3.1.2 |
| Word | python-docx | 1.1.0 |
| Bug | 禅道 SDK 直连 | utils/zentao_bug_manager |
| 通知 | webhook curl 直连 | utils/generate_report |
| MCP | filesystem | npm @modelcontextprotocol |
| AI | Claude 4.x（Opus 4.7 / Sonnet 4.6 / Haiku 4.5） | Claude Code 默认管理 |

---

## 八、版本特性总览

| 模块 | 说明 |
|------|------|
| 专家团队 | 8 位专家 + 1 位 test-lead 协调者 |
| 执行技能 | 8 个（含 jmeter-script-gen） |
| 重试策略 | 10/20/40s 指数退避（call_with_retry） |
| 测试数据 | Faker+Factory Boy；权威路径 `测试数据/test_data.json`；DataMasker 递归脱敏 |
| 环境管理 | test/staging 多环境（prod 禁用）；wiremock 3.3.1；指数退避重试 |
| Flaky 检测 | history 归档 + 离线 fail_rate_pct 检测；冒烟不开 reruns 保留信号 |
| 代码覆盖率 | pytest-cov 指向 `$APP_SRC_PATH`（被测系统源码，不指向测试脚本） |
| 并行执行 | pytest-xdist（默认 4 进程） |
| JMeter 性能 | 双模式（ci_quick / full）；TARGET_HOST 不含协议；JSONPostProcessor；If Controller 短路；阶梯加压 3 ThreadGroup；archive 下载兜底 |
| 性能基线 | `workspace/执行日志/baselines/perf_baseline.json`；release+full+PASS 才更新 |
| CI/CD | GitHub Actions + Jenkins；门禁统一调 utils；CSV 调 utils；secrets outputs 中转；PATH withEnv |
| 通知渠道 | 企微 / 飞书 / 钉钉 三端 webhook 直连（飞书合法颜色）；MCP 通道收口（仅 filesystem） |

---

## 九、常用命令速查

```
# 在 Claude Code 提示符（> 后是输入，不是 shell 命令）
> /smoke-test
> /test-coordinator
> /regression-test
> /testcase-design
> /python-script-gen
> /jmeter-script-gen
> /data-preparation
> /zentao-bug-submission
```

```bash
# pytest
APP_SRC="${APP_SRC_PATH:-./src}"

pytest -m "p0" -n 2 --timeout=60 -v                           # 冒烟（不开 reruns）

pytest -m "p0 or p1" -n 4 --reruns=2 --reruns-delay=5 \
    --cov="${APP_SRC}" --cov-report=html:workspace/执行日志/coverage-report \
    --cov-report=xml:workspace/执行日志/coverage.xml \
    --cov-fail-under=80                                        # 回归 + 覆盖率

pytest -m "(p0 or p1) and login"                              # 模块组合
pytest -m "api"                                                # 仅 API

# Allure
allure serve workspace/执行日志/allure-results

# JMeter（双模式见 PERF_MODE）
python -m utils.jmeter_result_parser <jtl> --mode ci_quick

# CI 门禁
python -m utils.ci_quality_gate \
    --smoke-xml workspace/执行日志/smoke-results.xml \
    --regression-xml workspace/执行日志/regression-results.xml \
    --coverage-xml workspace/执行日志/coverage.xml \
    --coverage-threshold 80

# 调试 UI（跨平台）
HEADLESS=false pytest -m "p0" -v                              # Linux/Mac
$env:HEADLESS="false"; pytest -m "p0" -v                      # Windows PowerShell

# Flaky 归档检测
python -m utils.flaky_detector --archive ... --history workspace/执行日志/history --limit 5
```

---

## 协议覆盖矩阵

| 协议 | 工具 | utils |
|------|------|-------|
| HTTP / HTTPS | requests | api_retry_util |
| WebSocket（同步/异步/重连/并发） | websocket-client + websockets | websocket_helper |
| gRPC | grpcio + 项目 proto | protocol_helper.grpc_call |
| TCP / UDP | socket 标准库 | protocol_helper.tcp_send_recv / udp_send_recv |
| GraphQL | requests + body | protocol_helper.graphql_query |
| SOAP | requests + envelope | protocol_helper.soap_call |
| MQTT | paho-mqtt | iot_helper.MQTTClient |
| SSH | paramiko | iot_helper.SSHClient |
| 串口 | pyserial | iot_helper.open_serial |
| Modbus | pymodbus | protocol_helper.modbus_read_holding |
| Kafka | kafka-python | mq_helper |
| RabbitMQ | pika | mq_helper |
| Jaeger / Zipkin（链路） | requests | tracing_validator |

---

## 多格式 PRD 输入（自动识别 + 路由）

`utils/prd_loader.py` 统一入口，支持：

| 格式 | 解析器 |
|------|-------|
| md / txt | 直读 |
| pdf | pdfplumber → PyPDF2 兜底 |
| docx | python-docx（含表格） |
| xlsx | openpyxl（多 Sheet 合并） |
| zip | 递归解包 |
| png/jpg | Claude Code 视觉 / OCR |
| html | BeautifulSoup |
| URL | requests + BS（私有空间需 PRD_HTTP_TOKEN） |

```python
from utils.prd_loader import load_prd, suggest_agents
info = load_prd("docs/PRD.pdf")
routing = suggest_agents(info["text"])
# {"platforms": [...], "recommended_agents": [...], "recommended_skills": [...]}
```

test-lead 收到 PRD 第一步即调此工具，自动选专家组合。

---

## 全链路覆盖矩阵（速览）

| 平台 | Agent | Skill | 工具栈 |
|------|-------|-------|------|
| Web + API + 数据库 | automation-engineer / data-preparer | python-script-gen | Playwright / requests / SQLAlchemy |
| 性能（双模式） | automation-engineer | jmeter-script-gen | JMeter（主） + Locust（备） |
| Mobile（Android/iOS/小程序） | mobile-tester | mobile-test | Appium + 微信 CLI |
| Desktop（Win/macOS/Electron） | desktop-tester | desktop-test | pywinauto + PyAutoGUI + Playwright Electron |
| 视觉/游戏 | visual-tester | visual-test | Airtest + OpenCV + Tesseract |
| 系统集成（IoT/音视频/Tracing/MQ） | system-tester | system-test | paramiko + paho-mqtt + FFmpeg + Jaeger + Kafka |
| AI/ML | ai-tester | ai-test | scikit-learn + scipy（漂移）+ LLM eval |

**全链路覆盖率：≈ 90%**

---

## 十、跨 AI 工具兼容性

Claude Code 是默认 / 推荐 runtime，**不强制绑定**。

| 组件 | Claude Code 依赖 | 跨工具适配 |
|------|----------------|----------|
| `.claude/agents/*.md` | ✅ Claude Code spec | Cursor `.cursorrules` / Continue `.continue/` / 通用 LLM 拼 system prompt |
| `.claude/skills/*.md` | ✅ Claude Code 独有 | 其他工具无对等机制 |
| `.mcp.json` | 半依赖 | MCP 协议跨工具（Claude Desktop / Cursor / OpenAI 系部分支持） |
| `Agent` 子专家工具 | ✅ Claude Code 独有 | 人工编排 / 多 agent 框架替代 |
| `utils/*.py`（12 个） | ❌ 纯 Python | **跨工具完全可用** |
| pytest / Playwright / JMeter / Allure | ❌ 跨工具 | **完全可用** |
| CI/CD（yml / groovy） | ❌ 跨工具 | **完全可用** |

**模型**：Claude 4.x 是推荐而非强制。项目代码不调任何 LLM API（utils 全工具代码）。

**迁移成本**：工程链零改动；agent/skill 文档需重写为目标工具格式。

---

## 十一、闭环约定

1. **数据**：`workspace/测试数据/test_data.json`（conftest fixture 直接消费，无日期）
2. **覆盖率**：cov 指向 `$APP_SRC_PATH`（被测系统源码）
3. **重试**：全栈统一 10/20/40s（utils/api_retry_util.call_with_retry）
4. **severity 映射**：1=P0 / 2=P1 / 3=P2 / 4=P3（utils/zentao_bug_manager 权威）
5. **error_rate 单位**：pct（字段名 `_pct` 后缀）
6. **基线**：仅 release+full+PASS 才更新 perf_baseline.json
7. **门禁**：smoke / regression / performance_full / performance_ci_quick 由 utils/ci_quality_gate 与 utils/jmeter_result_parser 统一
8. **MCP**：仅 filesystem；通知/Bug 走 SDK 直连
9. **prod**：get_current_env 直接 raise（防误测生产）
10. **Flaky vs reruns**：冒烟不开 reruns（保信号），回归开 reruns（快反馈），flaky 由 history 离线检测

---

## 十二、交付物速查（详见 `01-快速开始/交付物清单.md`）

| 提交场景 | 文件路径 | 责任专家 | 格式 |
|---------|---------|---------|------|
| 测试计划提交 | `workspace/测试计划/test_plan_{项目}_{YYYYMMDD}.md` | test-lead | Markdown（IEEE 829） |
| 需求分析报告 | `workspace/需求分析/requirements_analysis_*.md` | requirements-analyst | MD + JSON |
| 测试用例 | `workspace/测试用例/testcases_*.xlsx` | testcase-designer | Excel 4 Sheet |
| **测试报告（最终给管理层）** | `workspace/执行日志/报告/测试报告_*.docx` | report-generator | Word |
| Allure 功能报告 | `workspace/执行日志/allure-report/index.html` | test-executor + Allure | HTML |
| JMeter 性能报告 | `workspace/执行日志/jmeter-report/index.html` | test-executor + JMeter | HTML |
| 覆盖率报告 | `workspace/执行日志/coverage-report/index.html` | pytest-cov | HTML |
| Bug 列表 | 禅道（在线） + `workspace/执行日志/regression_summary.json` | bug-manager | 禅道 + JSON |

**关键提交物 = 测试计划 (md) + 测试报告 (docx) + 3 个 HTML 报告链接**。其余是支撑材料。

完整交付物清单（含 CI/CD 归档、提交自检、历史归档建议）见 `01-快速开始/交付物清单.md`。

---

> **文档版本管理**：本文件是单文件全嵌入版，作为备查/分发用。任一分目录文件改动后须同步本文件对应段落。详细完整内容请参考各分目录原文：
> - `02-专家定义/`、`03-技能定义/`、`04-配置文件/`、`05-代码示例/`、`06-CICD集成/`、`README.md`
