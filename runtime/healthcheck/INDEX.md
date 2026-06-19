# runtime/healthcheck/ 索引

> 4 层自检 · pre-tag 卡 release。

## 4 层结构

| 层 | 脚本 / hook | 跑什么 | 触发 | 成本 |
| ---- | ------------- | -------- | ------ | ------ |
| L1 | `agent_smoke.py` | frontmatter lint + 文件命名 + 注册表可加载 | pre-commit / pre-push / `tagent doctor --agents` | $0 |
| L2 | CI workflow `selftest-mock` | mock router 跑完 16 agent 编排 + e2e 落盘 | 每 push / PR | $0 |
| L3 | `tagent doctor --agents` / `tagent selftest --e2e` | 真 LLM 跑 16 agent + e2e | pre-tag 本地 | ~$4 / release |
| L4 | CI cron `selftest-weekly` | main 真 LLM e2e + 日志归档 | 周一 03:00 UTC | ~$16/月 |

## 接入

-**pre-push / pre-commit**:`.pre-commit-config.yaml` 已 wire `agent_smoke`

-**CLI**:

  ```bash
  tagent doctor --agents      # L1 + L3 真 LLM 16 agent
  tagent selftest --e2e       # L3 全 e2e 闭环
  ```

-**pre-tag**:`scripts/git-pre-tag.sh` 卡 `git tag v1.x` 命令(没跑 selftest 拒绝)

## 失败处置

| L1 失败 | 处置 |
| --------- | ------ |
| 文件命名不符 NN-name.md | 改名 + 同步 `runtime/registry/` 缓存 |
| frontmatter 缺字段 | 补 name/description/tools |
| 注册表 build_catalog raise | 看 traceback,fix yaml 语法 |
| count 不符(16 / ≥25) | 别误删了 |
| 序号有跳 | 补缺号或重排 |

| L2 失败 | 处置 |
| --------- | ------ |
| mock e2e 流程断 | 编排 bug,跑本地复现 |

| L3 / L4 失败 | 处置 |
| -------------- | ------ |
| LLM 调用 raise | 检查 API key + 网络 + 配额 |
| 输出 schema 不符 | router prompt 或 agent 描述质量回归 → 看日志归档对比 |

## 相关

- 自检
- `.pre-commit-config.yaml` 中 `forbid-private-source` / `forbid-essence-library` / `file-count-check` 协同
- 日志归档:`discussions/selftest_<version>_<timestamp>.log`
