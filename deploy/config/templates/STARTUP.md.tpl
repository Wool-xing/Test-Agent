# Test-Agent 启动指南(由 `tagent init` 生成)

> 配置:**{{TEST_TYPE_LABEL}}** · {{PLATFORM_LABEL}} · LLM={{LLM_PROVIDER}} · BugTracker={{BUG_TRACKER}} · 通知={{NOTIFIER_LIST}}
> 生成于 {{GENERATED_AT}} · Test-Agent {{TAGENT_VERSION}}

## 1. 填占位(必做)

打开 `.env`,把 `<your_*>` 占位替换成真值:

{{REQUIRED_FILLS_BLOCK}}

> 不填对应功能自动跳过(不阻塞 e2e),但通知 / Bug 提交不会发出。

## 2. 装依赖(按需)

```bash
pip install -r 04-配置文件/requirements.txt
{{PLATFORM_DEPS_HINT}}
```

## 3. 健康检查

```bash
tagent doctor              # 看配置 + DB + MinIO
tagent doctor --agents     # L1 frontmatter lint(无 LLM,< 5s)
```

## 4. 烟雾跑通

```bash
# 干跑(stub LLM,0 成本,验编排)
TAGENT_LLM_PROVIDER=stub tagent selftest --e2e

# 真跑(用上面配的 LLM)
tagent run "{{SAMPLE_TARGET}}" --mode learn
```

## 5. 推荐 skill 顺序

{{RECOMMENDED_SKILLS_NUMBERED}}

## 6. 出错怎么办

| 症状 | 处置 |
|------|------|
| `LLM 调用 raise` | 检查 API key + 网络;切 `TAGENT_LLM_PROVIDER=ollama` 离线兜底 |
| `BugTracker 提交失败` | 占位没填或网络 / 权限错;不阻塞,但日报会少 |
| `通知没发出` | 至少配 1 个渠道;未配自动跳过 |
| `selftest n7 失败` | 装 python-docx:`pip install python-docx` |

## 7. 下一步

- 看 `examples/web-demo/` 5 分钟跑通最小例
- 看 `01-快速开始/INDEX.md` 完整流程
- 看 `docs/INDEX.md` 找样式 / 理论 KB

---

`tagent init` 重跑可覆盖此文件。手工编辑后请别再跑(或备份)。
