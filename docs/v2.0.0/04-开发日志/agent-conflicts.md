# Agent 冲突记录

> 按提示词 §四-B 要求，记录多 Agent 协作中产生的冲突。
> **格式:** 日期 + 冲突描述 + 涉及Agent + 根因 + 解决措施
> **原则:** 不隐瞒、不美化、不重复犯同样错误

---

## 冲突记录

| # | 日期 | 冲突描述 | 涉及Agent | 根因 | 解决措施 |
|---|------|---------|----------|------|---------|
| 1 | 2026-06-20 | 多个Agent同时修改 `runtime/router/prompt.py` 导致合并冲突 | planner, code-reviewer, tdd-guide | 未按顺序串行执行，3个Agent同时编辑同一文件 | 建立文件级锁：同一文件同一时间只允许1个Agent编辑 |
| 2 | 2026-06-20 | Agent A 删除了 Agent B 刚创建的测试文件 | refactor-cleaner, tdd-guide | refactor-cleaner 误判新测试为空壳文件 | 新增文件24小时内禁止自动删除；cleaner需人工确认 |
| 3 | 2026-06-20 | 安全审查agent的修复破坏了功能测试 | security-reviewer, test-executor | 安全修复（输入转义）改变了API契约，测试期望原值 | 安全修复后必须重跑全量测试，不得跳过 |
| 4 | 2026-06-21 | 文档更新agent覆盖了代码修复agent的修改 | doc-updater, build-error-resolver | doc-updater从旧版本重新生成文档，覆盖了手动修正 | 文档自动生成前检查最新commit，避免覆盖当天修改 |
| 5 | 2026-06-21 | 性能优化与安全加固互斥 | performance-optimizer, security-reviewer | 性能优化移除了输入验证缓存（认为冗余），安全审查要求加回 | 涉及安全+性能的改动需双人签字（security + perf 同时 approve） |
| 6 | 2026-06-21 | 并行Agent上下文溢出导致3个子任务丢失 | test-lead, 3 worker agents | 主Agent上下文超限compact后，子Agent的待办事项丢失 | 关键任务列表写入文件（CHECKPOINT），不依赖Agent记忆 |
| 7 | 2026-06-22 | git rm --cached -r . 后所有文件被标记为deleted+new，影响Agent文件判断 | user (manual), 全Agent | 用户手动执行索引清理，Git检测到所有文件变更 | 大型Git操作前先通知，操作后运行 `git reset --hard` 恢复 |

## 冲突分类统计

| 类型 | 次数 | 最严重 |
|------|------|--------|
| 并发编辑冲突 | 2 | 文件损坏 (冲突1) |
| 误删/覆盖 | 2 | 代码丢失 (冲突2, 4) |
| 安全 vs 功能 | 1 | 测试失败 (冲突3) |
| 安全 vs 性能 | 1 | 功能退化 (冲突5) |
| 上下文丢失 | 1 | 任务遗漏 (冲突6) |
| 人为操作 | 1 | 全量文件标记 (冲突7) |

## 已建立的防护机制

1. **文件变更通知**: 任何Agent修改文件后通知所有活跃Agent
2. **24小时保护期**: 新文件创建后24小时内不可被自动删除
3. **双签制度**: 安全+性能冲突的改动需双方approve
4. **CHECKPOINT落盘**: 关键任务列表写入文件，不依赖Agent记忆
5. **全量回归**: 安全修复后必须跑全量测试

## 待建立

- [ ] Agent间实时状态共享（当前靠CHECKPOINT文件轮询）
- [ ] 文件级编辑锁（技术实现：基于.git/index.lock扩展）
- [ ] 冲突自动检测+通知（检测到并发编辑时自动暂停）

---

*最后更新: 2026-06-22 | 按 §四-B 协议维护*
