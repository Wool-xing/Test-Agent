---
name: verification-loop
description: 5-phase 验证循环 Skill:build → typecheck → lint → test → coverage。任意失败 STOP + 修。派生自 ECC 同名 skill 。PR 前 / 质量门禁前 / refactor 后必跑。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# verification-loop

> 对标: Superpowers verification-before-completion

## 铁律 (Iron Law)

```
无新鲜验证证据 = 不得声称完成
```

**声称"通过"但没有刚跑过的验证输出 = 说谎，不是效率。**

跳过以下任一步骤 = 没有验证:
1. **识别**: 什么命令能证明这个声称?
2. **运行**: 执行完整命令 (新鲜输出，不是上次的)
3. **读取**: 完整输出，检查退出码，统计失败数
4. **验证**: 输出是否证实了声称?
   - 否 → 报告实际状态+证据
   - 是 → 报告声称+证据
5. **然后才能**: 做出声称

## 常见失败模式

| 声称 | 需要 | 不够 |
|------|------|------|
| 测试通过 | `pytest` 输出: 0 failures | "上次跑的"、"应该过了" |
| 构建成功 | 构建命令: exit 0 | linter过了、"看起来没问题" |
| Bug修好 | 复现原始症状: 通过 | "代码改了"、"应该修好了" |

## 红旗 — 立即停止

- 使用"应该"、"可能"、"似乎"
- 在验证前表达满意 ("好了！"、"完成了！")
- 准备提交/推送但没验证
- 信任agent的"成功"报告
- "就这一次"、"我累了"、任何借口

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

```text

失败 → STOP

### Phase 2 · Type Check

```bash

# Python

mypy runtime/ 2>&1 | head -30
# 或 pyright

pyright runtime/ 2>&1 | head -30

```text

报所有 type errors;关键的修

### Phase 3 · Lint Check

```bash

ruff check runtime/ 2>&1 | head -30

```text

### Phase 4 · Test Suite

```bash

pytest runtime/tests/ -v 2>&1 | tail -50

```text

全过才进下一步

### Phase 5 · Coverage

```bash

pytest --cov=runtime --cov-report=term-missing 2>&1 | tail -30

```text

对比 regression 门槛 cov ≥ 80%

## 融合

- 五层门禁:本 skill 是**进 smoke → regression**的前置
- 修改四关:四关 = 本 skill 4 阶段简化版
- 横切可复现性:失败必固定 seed + snapshot

## 不做

- 不跳阶段
- 不忽略 type 错误"等会儿再修"
- 不静默吞 lint warning(--fix 默认开)
