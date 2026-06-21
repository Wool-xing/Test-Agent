# Skill 开发指南 — Test-Agent V2.0.0

> Sprint 3: 扩展体系 | 目标: 开发者30分钟内创建→测试→发布第一个Skill

---

## 快速开始 (5分钟)

```bash
# 1. 创建新Skill脚手架
mkdir my-check && cd my-check

# 2. 创建 SKILL.md (必需——Skill的入口文件)
cat > SKILL.md << 'EOF'
---
name: my-check
version: 1.0.0
display_name: My Check
description: Check that my service is healthy
permissions:
  network: restricted
  filesystem: none
  shell: none
  timeout: 30
---
# My Check

Check if my service responds correctly.

## Quick Start
```bash
tagent "run my-check against staging"
```
EOF

# 3. 创建 executor.py (可选——执行逻辑)
cat > executor.py << 'EOF'
def execute(params, ctx):
    import urllib.request
    url = params.get("url", "http://localhost:8080/health")
    resp = urllib.request.urlopen(url, timeout=10)
    return {
        "status": "pass" if resp.getcode() == 200 else "fail",
        "summary": f"{url} returned {resp.getcode()}",
        "details": {"url": url, "status_code": resp.getcode()},
        "checks": [{"name": "HTTP 200", "expected": 200, "actual": resp.getcode(), "pass": resp.getcode() == 200}],
        "error": None,
    }

# 4. 安装到本地workspace
tagent skill install ./my-check

# 5. 运行测试
tagent skill test my-check

# 6. 使用
tagent "run my-check against staging"
```

## SKILL.md 规范

### 必填字段 (YAML frontmatter)

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 唯一标识符, kebab-case |
| version | string | 语义化版本 (SemVer) |
| display_name | string | 人类可读名称 |
| description | string | 一句话描述 (≤80字符) |
| permissions | object | 权限声明 (必填) |

### 权限声明

```yaml
permissions:
  network: none | localhost | restricted | any
  filesystem: none | read | readwrite
  shell: none | readonly | full
  timeout: 60  # 秒
```

### 推荐字段

- `tags`: 搜索标签 (2-5个)
- `icon`: 单emoji
- `compatible.platforms`: [windows, macos, linux]
- `compatible.modes`: [community, enterprise]

## executor.py 规范

```python
def execute(params: dict, ctx) -> dict:
    """Execute the skill logic.

    Args:
        params: Input parameters from user/tagent config.
        ctx: ExecutionContext (optional, for advanced use).

    Returns:
        Dict with required fields:
        {
            "status": "pass" | "fail" | "error" | "timeout" | "skipped",
            "summary": "One-line result summary",
            "details": {...},  # Arbitrary detail data
            "checks": [{"name": str, "expected": any, "actual": any, "pass": bool}],
            "error": None | "ERROR-CODE: message"
        }
    """
```

## 测试 Skill

```bash
# 创建 test_<skill_name>.py
cat > test_my_check.py << 'EOF'
from executor import execute

def test_valid_url():
    result = execute({"url": "https://httpbin.org/get"}, None)
    assert result["status"] in ("pass", "error")

def test_invalid_url():
    result = execute({"url": "not-a-url"}, None)
    assert result["status"] == "error"

def test_missing_url():
    result = execute({}, None)
    assert result["status"] == "error"

# Run: python -m pytest test_my_check.py
EOF
```

## 打包与发布

```bash
# 打包为 .tar.gz
python -c "from runtime.sdk import package_skill; package_skill('my-check', '.')"

# 本地安装
tagent skill install ./my-check

# 发布到本地市场
python -c "from runtime.sdk import publish_skill; publish_skill('my-check.tar.gz', 'workspace/marketplace')"
```

## 示例参考

| Skill | 目录 | 说明 |
|-------|------|------|
| demo-http | `examples/skills/demo-http/` | HTTP健康检查 |
| demo-file | `examples/skills/demo-file/` | 文件存在性/大小验证 |
| demo-notify | `examples/skills/demo-notify/` | 通知发送测试 |

## 命令速查

| 命令 | 说明 |
|------|------|
| `tagent skill list` | 列出已安装Skill |
| `tagent skill search <kw>` | 搜索Skill |
| `tagent skill install <path>` | 安装本地Skill |
| `tagent skill test <name>` | 运行Skill测试 |

---
*文档创建: 2026-06-21 | Sprint 3*
