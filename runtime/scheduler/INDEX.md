# scheduler 索引

> 让 Test-Agent 不只响应人,**自己定时跑**——日报 / 夜审 / 每周回归 / 月度合规检查。

## 文件清单

| 文件 | 用途 |
| ------ | ------ |
| `jobs.py` | Job 存储(`workspace/cron/jobs.json`)+ croniter 解析 |
| `scheduler.py` | tick() 每 60s,跨平台文件锁(fcntl/msvcrt) |
| `injection_scan.py` | 运行时 prompt 注入扫描(防 skill 加载注入) |

## 规则

- **运行时全 prompt 扫描**(非仅 create-time):skill 在 runtime 加载,恶意 skill 可携带注入
- **文件锁防重入**:`workspace/cron/.tick.lock` 双栈实现
- **输出可追溯**:`workspace/cron/output/{job_id}/{ts}.md`
- **不静默崩**:扫描失败 → 落 `decisions/` + 输出 "job blocked"

## 与现有运行时关系

- 调用 `runtime/api/deps.Kernel` 执行被调度任务(复用现有路由+编排)
- 输出走 `runtime/storage/repo` 入飞轮
- 通知走 `runtime/gateway/`(M3-5)分发到平台
