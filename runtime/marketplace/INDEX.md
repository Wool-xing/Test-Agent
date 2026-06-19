# runtime/marketplace 索引

## 文件清单

| 文件 | 用途 |
| ------ | ------ |
| `catalog.py` | 加载 `marketplace/registry.json` + 索引 |
| `client.py` | 查询(local + 远程 registry mirror) |
| `verifier.py` | 4 关安全门(sig + scan + sandbox + darwin) |
| `installer.py` | 装 / 卸 / 归档 |
| `cli.py` | tagent CLI 子命令绑定(install/search/verify/list/uninstall) |

## 4 关门顺序

```text
用户 tagent install X
    ↓

1. catalog 查 X 元数据
    ↓

2. verifier.signature_check       # 关 1 签名(必)
    ↓

3. verifier.injection_scan        # 关 2 注入扫
    ↓

4. verifier.sandbox_dry_run       # 关 3 沙箱
    ↓

5. verifier.darwin_score          # 关 4 评分(≥75)
    ↓

6. installer.install              # 落地到 marketplace/{lane}/X/
    ↓

7. registry.json 更新
    ↓

8. decisions/ 落安装记录

```text

任一关失败 → 全部回滚 + decisions/ 落原因。

## 融合原则

- 决策不可逆禁止:卸载只归档(`marketplace/.archive/`)
- safe-by-default:`tagent.yml marketplace.enabled` 默认 false
- Karpathy 原则 3 Surgical:卸载只动安装时建的文件,不动相邻
- Essence watcher:可关联 marketplace 远程 registry 自动同步
