---
name: verification-loop
description: "5-phase 验证循环 Skill:build → typecheck → lint → test → coverage。任意失败 STOP + 修。派生自 ECC 同名 skill。PR 前 / 质量门禁前 / refactor 后必跑。"
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# verification-loop

## 触发

- feature 完成后
- PR 提交前
- 质量门禁前
- refactor 后
- darwin-skill 评分前

## 5 Phase(任意失败 STOP)

### Phase 1 · Build Verification
```bash
# 本项目:runtime/ 子包
pip install -e ./runtime 2>&1 | tail -20
```
失败 → STOP

### Phase 2 · Type Check
```bash
# Python
mypy runtime/ 2>&1 | head -30
# 或 pyright
pyright runtime/ 2>&1 | head -30
```
报所有 type errors;关键的修

### Phase 3 · Lint Check
```bash
ruff check runtime/ 2>&1 | head -30
```

### Phase 4 · Test Suite
```bash
pytest runtime/tests/ -v 2>&1 | tail -50
```
全过才进下一步

### Phase 5 · Coverage
```bash
pytest --cov=runtime --cov-report=term-missing 2>&1 | tail -30
```
对比 regression 门槛 cov ≥ 80%

## 与融合

- 五层门禁:本 skill 是**进 smoke → regression** 的前置
- 修改四关:四关 = 本 skill 4 阶段简化版
- 横切可复现性:失败必固定 seed + snapshot

## 不做

- 不跳阶段
- 不忽略 type 错误"等会儿再修"
- 不静默吞 lint warning(--fix 默认开)
