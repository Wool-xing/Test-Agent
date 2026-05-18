# LLM 模型 Provider 配置手册

> Test-Agent 任 LLM 厂商即插即用. 国内国外, 商业开源, 云端本地, 全支持. **零代码改动**, 只改 env.

---

## 🚀 30 秒了解

- **是什么**: 配置 Test-Agent 后端 LLM 的速查手册. 国内国外 11+ 厂商可用.
- **几步上手**:
  1. 选厂商 (路径 A 内置 6 / 路径 B 兼容 5+)
  2. 复制对应 export
  3. `tagent demo` 验路由
- **实测有效** (V1.36.0): Claude / OpenAI / Gemini / DeepSeek / Qwen / Ollama / **智谱 GLM** (路径 B 实测 20/20 准, 见 PR #79)
- **适用场景**:
  - 离线本地 = Ollama / Qwen
  - 国内合规 = 智谱 / 豆包 / 通义
  - 性价比 = DeepSeek / Kimi
  - 主备 fallback = 多 provider 接管 (见 §3)

---

## 0 · 两条接入路径

| 路径 | 适用 | 配置 env |
|---|---|---|
| **A · 内置 provider** | litellm 已内置 (6 厂商) | `TAGENT_LLM_PROVIDER` + 厂商标准 key env |
| **B · OpenAI 兼容兜底** | litellm 未内置但提供 OpenAI 兼容端点 (智谱/豆包/Kimi/百川/讯飞 等) | `TAGENT_LLM_PROVIDER=openai/<model>` + `TAGENT_LLM_API_BASE` + `TAGENT_LLM_API_KEY` |

两路径**共存**, 不冲突, 不需选边.

---

## 1 · 路径 A — 内置 6 厂商

### 1.1 Claude (Anthropic)

```bash
export TAGENT_LLM_PROVIDER=claude
export ANTHROPIC_API_KEY=sk-ant-xxx
# 默认 model: anthropic/claude-sonnet-4-6 (改: 编辑 runtime/router/llm_client.py PROVIDER_MODEL_MAP)
```

注册: https://console.anthropic.com/ · 价格档: Sonnet 4.6 = 输入 $3/1M tok, 输出 $15/1M tok

### 1.2 ChatGPT (OpenAI)

```bash
export TAGENT_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-xxx
# 默认 model: openai/gpt-4o
```

注册: https://platform.openai.com/ · gpt-4o = 输入 $2.5/1M, 输出 $10/1M

### 1.3 Gemini (Google)

```bash
export TAGENT_LLM_PROVIDER=gemini
export GEMINI_API_KEY=xxx
# 默认 model: gemini/gemini-1.5-pro
```

注册: https://aistudio.google.com/apikey · 免费档每分钟 15 RPM

### 1.4 DeepSeek

```bash
export TAGENT_LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-xxx
# 默认 model: deepseek/deepseek-chat
```

注册: https://platform.deepseek.com/ · 国内价格优势 = 输入 ¥0.5/1M, 输出 ¥2/1M

### 1.5 Qwen (阿里通义)

```bash
export TAGENT_LLM_PROVIDER=qwen
export DASHSCOPE_API_KEY=sk-xxx
# 默认 model: dashscope/qwen-plus
```

注册: https://dashscope.console.aliyun.com/ · qwen-plus 较便宜, qwen-max 较强

### 1.6 Ollama (本地)

```bash
# 先启动 Ollama 服务并拉模型
ollama serve &
ollama pull qwen2.5:7b

export TAGENT_LLM_PROVIDER=ollama
# 默认 model: ollama/qwen2.5:7b (改 PROVIDER_MODEL_MAP 切其他)
```

下载: https://ollama.com/ · 完全本地, 0 API 费, 需 GPU/CPU 算力

---

## 2 · 路径 B — OpenAI 兼容兜底

litellm 未内置但厂商提供 OpenAI 兼容端点. 任 OpenAI SDK 能调的, 此处都能用.

### 2.1 智谱 GLM (清华系)

```bash
export TAGENT_LLM_PROVIDER=openai/glm-4-flash      # 或 glm-4-plus / glm-4-air
export TAGENT_LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
export TAGENT_LLM_API_KEY=<your_zhipu_key>
```

注册: https://open.bigmodel.cn/ · glm-4-flash **免费** · glm-4-plus / glm-4-air 收费

### 2.2 豆包 (字节火山引擎)

```bash
export TAGENT_LLM_PROVIDER=openai/<endpoint_id>     # 火山控制台创"在线推理接入点"得 endpoint_id
export TAGENT_LLM_API_BASE=https://ark.cn-beijing.volces.com/api/v3
export TAGENT_LLM_API_KEY=<your_ark_api_key>
```

注册: https://www.volcengine.com/product/ark · 国内大厂底座, 豆包 Pro / Lite / Vision 系列齐全

### 2.3 Kimi (月之暗面)

```bash
export TAGENT_LLM_PROVIDER=openai/moonshot-v1-8k    # 或 moonshot-v1-32k / moonshot-v1-128k
export TAGENT_LLM_API_BASE=https://api.moonshot.cn/v1
export TAGENT_LLM_API_KEY=sk-xxx
```

注册: https://platform.moonshot.cn/ · 长上下文擅长 (128k 支持)

### 2.4 百川

```bash
export TAGENT_LLM_PROVIDER=openai/Baichuan4         # 或 Baichuan4-Turbo / Baichuan3-Turbo
export TAGENT_LLM_API_BASE=https://api.baichuan-ai.com/v1
export TAGENT_LLM_API_KEY=sk-xxx
```

注册: https://platform.baichuan-ai.com/

### 2.5 讯飞星火 (Spark)

```bash
export TAGENT_LLM_PROVIDER=openai/general            # 或 generalv3 / generalv3.5 / 4.0Ultra
export TAGENT_LLM_API_BASE=https://spark-api-open.xf-yun.com/v1
export TAGENT_LLM_API_KEY=<APIPassword_from_console>  # 注: 是控制台"APIPassword" 不是 APIKey
```

注册: https://xinghuo.xfyun.cn/sparkapi · 注意鉴权方式与其他厂商略不同

### 2.6 通用模板 (任新厂商)

```bash
export TAGENT_LLM_PROVIDER=openai/<model_name>
export TAGENT_LLM_API_BASE=<openai_compatible_endpoint>
export TAGENT_LLM_API_KEY=<your_key>
```

只要厂商文档说"OpenAI 兼容" / "OpenAI SDK 可用", 填 3 个 env 即用. 无需改代码.

---

## 3 · .env 文件示例

将选定厂商配置写入项目根 `.env` (从 `.env.example` 复制后填):

```dotenv
# 选 1: Claude
TAGENT_LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxx

# 选 2: DeepSeek
TAGENT_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxx

# 选 3: 智谱 GLM-4-Flash (免费)
TAGENT_LLM_PROVIDER=openai/glm-4-flash
TAGENT_LLM_API_BASE=https://open.bigmodel.cn/api/paas/v4
TAGENT_LLM_API_KEY=<your_zhipu_key>

# 选 4: 离线开发 (无 key)
TAGENT_LLM_PROVIDER=stub
```

`.env` 不入 Git (`.gitignore` 已护). 多 key 可同时填, 只生效 `TAGENT_LLM_PROVIDER` 选中的那个.

---

## 4 · Fallback 配置 (主备厂商)

主厂商失败自动切备用. env:

```bash
export TAGENT_LLM_PROVIDER=claude              # 主
export TAGENT_LLM_PROVIDER_FALLBACK=deepseek   # 备
export ANTHROPIC_API_KEY=sk-ant-xxx
export DEEPSEEK_API_KEY=sk-xxx
```

`route_with_vote()` 多模型投票详见 `runtime/router/router.py`.

---

## 5 · 多模型投票 (高精度场景)

`test_router_two_model_vote_95pct` 实测 claude + qwen 双模型投票, 路由准确率 95%+.

```python
from runtime.router.router import route_with_vote
decision = route_with_vote(artifact, providers=["claude", "deepseek"])
```

要求两厂商 key 均设. 详见 `runtime/tests/test_router_real.py`.

---

## 6 · 验证 provider 可用

```bash
# 1. stub 离线验 (无 key)
TAGENT_LLM_PROVIDER=stub pytest runtime/tests/test_router.py -v

# 2. 真 LLM 验 (设 TAGENT_REAL_LLM=1 突破 conftest 隔离)
TAGENT_REAL_LLM=1 TAGENT_LLM_PROVIDER=<provider> <KEY_ENV>=<value> \
    pytest runtime/tests/test_router_real.py::test_router_single_model_accuracy_85pct -v -s
```

路径 B 还需加 `TAGENT_LLM_API_BASE` + `TAGENT_LLM_API_KEY`.

---

## 7 · 速查表 (10+ 厂商)

| 厂商 | 路径 | provider | api_base | key env |
|---|---|---|---|---|
| Claude | A | `claude` | (内置) | `ANTHROPIC_API_KEY` |
| ChatGPT | A | `openai` | (内置) | `OPENAI_API_KEY` |
| Gemini | A | `gemini` | (内置) | `GEMINI_API_KEY` |
| DeepSeek | A | `deepseek` | (内置) | `DEEPSEEK_API_KEY` |
| Qwen | A | `qwen` | (内置) | `DASHSCOPE_API_KEY` |
| Ollama | A | `ollama` | (本地) | 无 |
| 智谱 GLM | B | `openai/glm-4-flash` | `https://open.bigmodel.cn/api/paas/v4` | `TAGENT_LLM_API_KEY` |
| 豆包 | B | `openai/<endpoint_id>` | `https://ark.cn-beijing.volces.com/api/v3` | `TAGENT_LLM_API_KEY` |
| Kimi | B | `openai/moonshot-v1-8k` | `https://api.moonshot.cn/v1` | `TAGENT_LLM_API_KEY` |
| 百川 | B | `openai/Baichuan4` | `https://api.baichuan-ai.com/v1` | `TAGENT_LLM_API_KEY` |
| 讯飞星火 | B | `openai/4.0Ultra` | `https://spark-api-open.xf-yun.com/v1` | `TAGENT_LLM_API_KEY` |
| 其他 OpenAI 兼容 | B | `openai/<model>` | 厂商提供 | `TAGENT_LLM_API_KEY` |

---

## 8 · 故障排查

| 症状 | 原因 | 修法 |
|---|---|---|
| `LLM Provider NOT provided` | model 名 litellm 不识 | 用 `openai/<model>` 前缀走路径 B |
| `Authentication error` | key 错或未设 | 检 `echo $<KEY_ENV>` |
| `RateLimitError: 余额不足` | 厂商账户欠费 | 充值或换免费档 model (e.g., glm-4-flash) |
| 测试 `accuracy < 85%` | 模型路由能力弱 | 换更强 model 或用 `route_with_vote` 多模型投票 |
| `CERTIFICATE_VERIFY_FAILED` (litellm cost map) | 本地证书库缺 | 不影响调用, 仅 cost 计算降级, 可忽略 |

---

## 9 · 相关文档

- 配置清单全字段: `01-快速开始/配置清单.md`
- LLM 客户端实现: `runtime/router/llm_client.py`
- 路由策略详情: `runtime/router/router.py`
- 测试基线: `runtime/tests/test_router_real.py`
