# 测试覆盖率基线 — Sprint 0

> **日期:** 2026-06-20
> **方法:** pytest --cov=runtime

## 基线数据

```
测试总数: ~780 passed
覆盖率: 34% (runtime/ 30,337 lines total)
```

## 分解

| 模块 | Lines | 覆盖 | 覆盖率 |
|------|-------|------|--------|
| runtime/cli/ | ~3,500 | ~2,100 | ~60% |
| runtime/orchestrator/ | ~2,800 | ~1,400 | ~50% |
| runtime/infra/ (新增) | ~1,500 | ~1,200 | ~80% |
| runtime/router/ | ~1,200 | ~400 | ~33% |
| runtime/api/ | ~2,000 | ~300 | ~15% |
| runtime/agent/ (新增) | ~400 | ~300 | ~75% |
| runtime/core/ (新增) | ~150 | ~100 | ~67% |
| utils/ | ~8,000 | ~2,000 | ~25% |

## Sprint 1 目标

- 基线: 34%
- 目标: ≥34% (不能下降)
- 已达标 ✅

## 注释

- 新增infra/agent/core模块覆盖率较高(67-80%)
- 已有的api/webhooks路径覆盖率低(15%)——Sprint 4补
- util/大量工具脚本覆盖率25%——随Skill增加自然提升
