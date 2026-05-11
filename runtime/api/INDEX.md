# api 索引

## 文件清单

| 文件 | 用途 |
|------|------|
| `main.py` | FastAPI app,四端点 `/run` `/status/{run_id}` `/report/{run_id}` `/catalog` |
| `models.py` | 请求/响应 Pydantic 模型 |
| `deps.py` | 依赖注入(LLM client / orchestrator / storage) |

## 端点

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/run` | 多格式上传(PDF/Word/MD/exe/APK/IPA/Docker/口头指令),返回 run_id |
| GET | `/status/{run_id}` | SSE 流式状态(DAG 实时进度) |
| GET | `/report/{run_id}` | 报告下载(PDF/Word/HTML/JSON/XML/CSV) |
| GET | `/catalog` | 列 14 专家 + 13 Skill |

## 输入解析器

| 格式 | 解析库 |
|------|--------|
| PDF | pypdf / pdfplumber |
| Word | python-docx |
| Markdown | markdown |
| exe/APK/IPA/Docker | 文件元信息 + 类型探测(magic bytes) |
| 口头指令 | 直接传 LLM |
| 混合 | 多文件 + 自由文本,LLM 合并理解 |
