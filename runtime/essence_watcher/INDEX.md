# essence_watcher 索引

> 自动追踪 `_精髓库/` 引用的所有 upstream repo 更新。
> 主宪章 §29 教学层加固之 essence 自动汲取。

## 文件清单

| 文件 | 用途 |
|------|------|
| `parser.py` | 解析 `_精髓库/INDEX.md` 提取 repo url |
| `tracker.py` | 跟踪 commit hash;状态存 `workspace/essence/state.json` |
| `delta_extractor.py` | LLM 萃取 README + 关键 files delta(用 aux_client) |
| `policy.py` | 加载 `_精髓库/_apply_policy.yaml` 决定提议范围 |
| `runner.py` | 主入口:周期 / 手动跑 |

## 流程

```
1. 读 _精髓库/INDEX.md       → list of (name, repo_url)
2. 读 state.json             → 上次记录 commit hash
3. gh API 查 upstream HEAD   → 新 commit?
4. 若新 commit:
   a. fetch README + key files diff
   b. LLM(aux) 萃取 delta
   c. 写 _精髓库/{name}.update_{date}.md
   d. 标 confidence: llm-draft-unreviewed
5. 应用 policy.yaml:
   - skill-related delta → 提议入 03-技能定义/
   - rule-related delta → 提议入主宪章 § 待审
   - 其他 → 仅入 _精髓库 不动 Test-Agent
```

## 启用

`tagent.yml`:
```yaml
essence_watcher:
  enabled: true             # safe-by-default,默认 false
  cron: "0 3 * * 1"         # 每周一凌晨 3 点
  apply_policy: default     # _精髓库/_apply_policy.yaml
  delta_min_lines: 20       # README 改动 < 20 行不触发萃取
```

## 选择性应用 policy(`_精髓库/_apply_policy.yaml`)

```yaml
# 哪些 delta 自动提议入 Test-Agent
auto_propose:
  - skill_definitions          # 新 skill 名字 / 描述 / 元数据 → 提议 03-技能定义/
  - charter_rules             # 主宪章规则更新 → 提议 §
  - safety_patterns           # 防护模式 → 提议 §24 safe-by-default
  - test_methodology          # 测试方法论新增 → 提议 §17/§21

# 仅入精髓库,不动 Test-Agent
essence_only:
  - branding
  - business_lane             # 商业版细节
  - deployment_specifics      # 部署细节
  - unrelated_features

# 永不入
never:
  - source_code_blocks > 100_lines  # 大段源码不抄
  - vendor_specific_apis             # 厂商锁定 API
```
