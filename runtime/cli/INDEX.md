# cli 索引

## 命令

```
tagent run <input>          # 跑测试
tagent plan <input>         # 仅规划路由, 不执行
tagent catalog              # 列 16 专家 + 32 Skill
tagent doctor               # 自检(LLM/DB/MinIO/Prefect 可达性)
```

## 直跑模式

不强制连 HTTP API,直接 import runtime 内核单进程跑(本地小项目快)。

```
tagent run <被测物>
```
