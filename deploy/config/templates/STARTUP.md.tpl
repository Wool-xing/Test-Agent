# Test-Agent 启动指南(由 `tagent init` 生成)

> 配置:**{{TEST_TYPE_LABEL}}** · {{PLATFORM_LABEL}} · LLM={{LLM_PROVIDER}} · BugTracker={{BUG_TRACKER}} · 通知={{NOTIFIER_LIST}}
> 生成于 {{GENERATED_AT}} · Test-Agent {{TAGENT_VERSION}}

## 1. 填占位(必做)

打开 `.env`,把 `<your_*>` 占位替换成真值:

{{REQUIRED_FILLS_BLOCK}}

> 不填对应功能自动跳过(不阻塞 e2e),但通知 / Bug 提交不会发出。

## 2. 装依赖(按需)

```bash
pip install -r requirements.txt
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

## 7. V2 新功能速览

| 命令 | 用途 |
|------|------|
| `tagent impact analyze --file <path>` | 知识图谱驱动的冲击分析 |
| `tagent impact recommend <files...>` | 智能测试推荐（改了什么测什么） |
| `tagent plugin new <name> --type skill` | 创建新插件/技能脚手架 |
| `tagent plugin install <name>` | 从 Marketplace 安装插件 |
| `tagent plugin list` | 查看已安装插件 |

> `specs/` 目录包含 ManifestV2 单源真理（所有 agent/skill 的定义）。
> `sdk/` 目录提供 Plugin SDK，支持自定义扩展。

## 8. 下一步

- 看 `examples/web-demo/` 5 分钟跑通最小例
- 跑 `tagent impact analyze --file utils/README.md` 体验冲击分析
- 看 `docs/site/` 完整文档站点（需 `cd docs/site && npm run dev`）
- 看 `docs/INDEX.md` 找样式 / 理论 KB

---

`tagent init` 重跑可覆盖此文件。手工编辑后请别再跑(或备份)。
