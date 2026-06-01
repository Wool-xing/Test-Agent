## 目标

删除 `.github/workflows/synthetic-monitor.yml` —— monitoring theater，长期红，无真实价值。

## 诊断

### 1. 表面问题（依赖缺失）

`pip install -e runtime/` 只装 runtime 自身依赖，跑 utils/ 时缺 `openpyxl` / `factory-boy` → 每次跑都 ModuleNotFoundError。

### 2. 设计层问题（核心）

- **4 "region" 全部跑同一台 GitHub-hosted Ubuntu runner**（`matrix.region` 只是 label，没有真分发到 us-east/us-west/eu-west/ap-southeast）
- 每 6 小时 × 4 假区 = **16 个红 run / 天**，吃 Actions minutes + 制造告警噪音
- 与 V1.43.0「防 mock 闭环 / 诚实化」主线冲突 —— monitoring theater 是 mock 的另一种形态

### 3. 已被 selftest-weekly 完整覆盖

| 维度 | synthetic-monitor | selftest-weekly |
|---|---|---|
| selftest --e2e | ✅ stub LLM | ✅ 真 LLM (Claude) |
| 频率 | 6 小时 (16 红/天) | 周一 03:00 UTC |
| 区域 | 假（4 region 同 runner） | 单 region (诚实) |
| 依赖装齐 | ❌ 缺 openpyxl/factory-boy | ✅ config/requirements.txt |
| Artifact 留存 | ❌ | ✅ 90 天 |
| 真 LLM probe | ❌ | ✅ doctor --probe |

## 处置

直接删除 `synthetic-monitor.yml`。selftest-weekly.yml 保留 smoke + e2e 覆盖。

## 不在本 PR 范围

- 如果未来真需要多 region synthetic monitoring，单独设计 + 真实跨地域分发（Vercel / Cloudflare Workers / 第三方监控服务），不再以 GitHub Actions matrix 假装。
