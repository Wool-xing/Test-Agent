# marketplace 索引

> 对标 Claude Code 官方 marketplace · 4 lane 资源库:skills / agents / mcp / hooks
> 用户按需下载;**4 关安全门必过**(签名 / prompt 扫 / 沙箱试跑 / darwin 评分)

## 4 lane

| Lane | 类型 | 路径 |
|------|------|------|
| **skills** | Claude Code 风 markdown skill | `marketplace/skills/` |
| **agents** | Subagent 定义 | `marketplace/agents/` |
| **mcp** | MCP server | `marketplace/mcp/` |
| **hooks** | hook 脚本 | `marketplace/hooks/` |

## 3 信任级源

| 级 | 来源 | 默认 confidence |
|----|------|----------------|
| **high** | Claude Code 官方 mirror(只镜像 metadata,不复制代码) | high |
| **medium** | 大厂源(Anthropic / OpenAI / Microsoft 公开 repo) | medium |
| **low** | 社区 GitHub PR | llm-draft-unreviewed → 双签升级 |

## 注册中心

`registry.json` 是 marketplace 总目录,每条 entry:

```json
{
  "name": "playwright-helper",
  "version": "1.0.3",
  "lane": "skills",
  "source_url": "https://github.com/.../skill.md",
  "sha256": "abc123...",
  "signature": "ed25519:...",
  "license": "MIT",
  "safety_score": 85,
  "confidence": "high",
  "source_tier": "high",
  "installed_at": null,
  "tags": ["test", "browser"]
}
```

## 安装命令

```bash
tagent search <kw>          # 搜
tagent list --lane skills   # 列已安装
tagent install skill <name> # 装(必过 4 关)
tagent verify <name>        # 单独跑沙箱验证
tagent uninstall <name>     # 卸(归档不删)
```

## 4 关安全门

1. **签名校验**:SHA256 + 可选 GPG/ed25519
2. **全 prompt 扫描**:`runtime/scheduler/injection_scan.py` 复用,扫 skill 文本
3. **沙箱试跑**:`runtime/backends/docker.py` 在 Docker 内跑 24h 观察
4. **darwin 评分**:`darwin-skill` 评 ≥75 才放行

任一不过 → 拒装 + 落 `decisions/`()

## 注意

- **不复制 Anthropic / OpenAI 源码**(品牌+协议红线)
- **仅镜像 metadata + 链接**到上游
- 卸载只**归档**到 `marketplace/.archive/`

## 配置

`tagent.yml`:
```yaml
marketplace:
  enabled: false              # safe-by-default
  trust_tiers: [high, medium] # low 默认拒
  safety_gates_required: 4    # 4 关全过
  registry_url: ""            # 远程 registry mirror(可选)
```
