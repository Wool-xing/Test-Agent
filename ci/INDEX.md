# ci 索引

> 顶层导航见根目录 `00-项目导航.md`；流水线配置详解见本目录 `CICD集成说明.md`。

## 文件清单

| 文件 | 用途 | 角色 |
| ------ | ------ | ------ |
| [CICD集成说明.md](CICD集成说明.md) | GitHub Actions + Jenkins 双流水线说明 + Secrets 清单 + 门禁 + 常见 Q&A | 阅读入口 |
| [github-actions-test.yml](github-actions-test.yml) | **用户分发模板**：部署到 `<PROJECT_ROOT>/.github/workflows/test.yml` 跑业务测试 | 模板 |
| [jenkins-pipeline.groovy](jenkins-pipeline.groovy) | **用户分发模板**：部署到 `<PROJECT_ROOT>/Jenkinsfile` 跑业务测试 | 模板 |

## 重要：双轨 CI 区分

本仓库存在两套 CI 配置，不要混淆：

| 配置位置 | 用途 | 谁跑 |
| --------- | ------ | ----- |
| `.github/workflows/ci.yml` | **本仓库自身 CI**：Ruff / 模板自检 / 文件统计 / 敏感文件防护 / 链接校验 | GitHub Actions（本 repo） |
| `.github/workflows/codeql.yml` | **本仓库自身 CodeQL**：python + actions 安全扫描 | GitHub Actions（本 repo） |
| `ci/github-actions-test.yml` | **用户分发模板**：用户 fork/部署后跑业务测试 | 用户自己的 repo |
| `ci/jenkins-pipeline.groovy` | **用户分发模板**：Jenkins 流水线 | 用户自己的 Jenkins |

> install.py 在部署时把 `ci/github-actions-test.yml` 拷贝到 `<PROJECT_ROOT>/.github/workflows/test.yml`，把 `jenkins-pipeline.groovy` 拷贝到 `<PROJECT_ROOT>/Jenkinsfile`。

## 流水线总览（用户分发模板）

```text
┌──────────────────────────────────────────────────────────┐
│ GitHub Actions / Jenkins  6 阶段 + 双模式分层             │
├──────────────────────────────────────────────────────────┤
│ 1. preflight  →  Secrets 自检（输出 outputs 中转）        │
│ 2. code-quality →  Ruff + 类型检查 + pip-audit + safety  │
│ 3. smoke-test  →  /smoke-test（≥95% 门禁）                │
│ 4. regression-test  →  P0+P1（≥90% + cov≥80% + Flaky）   │
│ 5. performance-test  →  JMeter 双模式（ci_quick / full）  │
│ 6. publish + quality-gate + notify  →  多端 webhook       │
└──────────────────────────────────────────────────────────┘
```

详见 [CICD集成说明.md](CICD集成说明.md)。

## 必须配置（开始流水线前）

| 项 | GitHub | Jenkins |
| ---- | -------- | --------- |
| 凭据 | Settings → Secrets and variables → Actions | Manage Jenkins → Credentials（Secret text） |
| Secret 清单 | 见 [CICD集成说明.md](CICD集成说明.md) "必须配置的 Secrets" 段 | 名称与 `Jenkinsfile::credentials('XXX')` 一一对应 |
| 触发条件 | push / PR / workflow_dispatch | SCM 轮询 / multibranch / 手动 |

## 常见问题速查

| 问题 | 答案 |
| ------ | ------ |
| Secrets 在 if 表达式判断永远 false | 已用 `preflight` job outputs 中转模式，详见 yml 注释 |
| Jenkins JMeter PATH 跨 sh 块丢失 | 用 `withEnv(["PATH+JMETER=..."])` 持久 PATH |
| 性能 CI 不达标 TPS≥100 | CI 默认 `ci_quick`（5 并发，门禁 TPS≥20）；`PERF_MODE=full` 切完整压测 |
| 性能基线何时更新 | 仅 `release/*` 分支 + `PERF_MODE=full` + 当次门禁全 PASS |
| 多端通知未发出 | `.env` / Secrets 未配 `WECHAT_WEBHOOK_URL` / `FEISHU_WEBHOOK` / `DINGTALK_WEBHOOK` / `SLACK_WEBHOOK_URL` / `EMAIL_SMTP_*` / `TEAMS_WEBHOOK_URL` 等；未配自动跳过不阻塞 |

## 同步链路

修改本目录任一文件时，**必须**联动检查：

| 修改 | 同步至 |
| ------ | -------- |
| `github-actions-test.yml` 加 stage | `CICD集成说明.md` 流水线表 + `配置清单.md` Secrets 表 |
| `jenkins-pipeline.groovy` 加 credentials | `CICD集成说明.md` Jenkins Credentials 段 |
| 门禁阈值变更 | `utils/ci_quality_gate.py::GATES` + `utils/jmeter_result_parser.py::DEFAULT_GATES_*` + `agents/01-测试主管.md::QUALITY_GATES` |
