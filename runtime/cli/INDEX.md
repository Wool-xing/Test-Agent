# cli 索引

## 命令

```
tagent run <input>          # 跑测试,input 可多次
tagent status <run_id>      # 实时状态
tagent report <run_id>      # 出报告(--format pdf|word|html|json|xml|csv)
tagent catalog              # 列 16 专家 + 32 Skill
tagent doctor               # 自检(LLM/DB/MinIO/Prefect 可达性)
```

## 直跑模式

不强制连 HTTP API,直接 import runtime 内核单进程跑(本地小项目快)。

```
tagent run examples/web-demo --local
```
