---
name: zentao-bug-submission
description: BugTracker Bug 提交技能。输入 Bug 描述或测试失败信息，自动规范化 Bug 报告并提交到所选 BugTracker，支持批量提交和状态追踪。默认实现 utils/zentao_bug_manager.py（severity 1=P0/2=P1/3=P2/4=P3）。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: script
---

# 禅道 Bug 提交

## 触发方式

```text
/zentao-bug-submission [Bug 描述 或 测试失败日志]
```

## 🔔 调用前置准备

```text
□ 禅道实例可访问（ZENTAO_BASE_URL）
□ .env 填 ZENTAO_ACCOUNT / ZENTAO_PASSWORD（API 凭证）
□ 禅道 API v1 已启用（管理后台 → 二次开发 → API）
□ 已知产品 ID（product 字段必填，禅道后台查）
□ Bug 描述含必备字段：title / 复现步骤 / 预期 / 实际
□ utils/zentao_bug_manager.py + utils/api_retry_util.py 已部署
□ 批量场景：test-executor 已输出 regression_summary.json（含 failures 列表）
```

## 执行流程

### Step 1：Bug 信息规范化（bug-manager 执行）

```text
- 确定 Bug 优先级（P0/P1/P2/P3）
- 提取复现步骤
- 整理预期/实际结果
- 识别影响范围
- 准备附件（截图/日志）
```

### Step 2：提交禅道（utils/zentao_bug_manager.py）

```text
- 自动指数退避重试（10s/20s/40s）
- token 失效自动续期
- 返回禅道 Bug ID
- 更新本地追踪记录
```

## 优先级 → severity / pri 映射（权威表）

| 优先级 | severity | pri | 标准 |
|-------|----------|-----|------|
| P0 | 1 | 1 | 核心业务流程完全阻断 / 数据丢失 / 安全漏洞 / 系统崩溃 |
| P1 | 2 | 2 | 主要功能受影响（有临时绕过）/ 关键数据展示错误 / 权限失效 |
| P2 | 3 | 3 | 次要功能异常 / UI 明显问题 / 错误提示不友好 / 性能低于预期 |
| P3 | 4 | 4 | 文案错误 / 微小 UI 瑕疵 / 体验优化建议 |

定义在 `utils/zentao_bug_manager.SEVERITY_MAP` / `PRI_MAP`。

## 单条提交

```python
from utils.zentao_bug_manager import ZentaoBugManager, SEVERITY_MAP, PRI_MAP

manager = ZentaoBugManager()  # 自动从 .env 读取凭证

bug = manager.create_bug({
    "title": "登录模块-正确密码登录后跳转 404",
    "product": 1,
    "severity": SEVERITY_MAP["P0"],
    "pri":      PRI_MAP["P0"],
    "type": "codeerror",
    "steps": "1. 打开登录页\n2. 输入账号密码\n3. 点击登录\n\n预期：跳转首页\n实际：404",
    "buildFound": "v1.0.0",
    "assignedTo": "frontend-lead",
})
print(f"Bug 已提交：#{bug.get('id')}")
```

## 批量提交（从 test-executor 输出 JSON）

```python
import json

from utils.zentao_bug_manager import ZentaoBugManager

manager = ZentaoBugManager()

with open("workspace/测试报告/{项目名}/regression_summary.json", encoding="utf-8") as f:
    results = json.load(f)

submitted = manager.batch_submit_from_failures(
    failures=results["failures"],         # 包含 case_id/case_name/priority/steps/module/failure_type
    product_id=1,
    build_version=results.get("build_version", "unknown"),
)
# submitted: [{"case_id": ..., "bug_id": ..., "priority": "P0", "status": "submitted"}, ...]
print(json.dumps(submitted, ensure_ascii=False, indent=2))
```

## Bug 状态追踪

```python
def track_bug_status(bug_ids: list) -> dict:
    """追踪 Bug 修复状态"""
    manager = ZentaoBugManager()
    status_map = {}
    for bug_id in bug_ids:
        try:
            bug = manager.get_bug(bug_id)
            status_map[bug_id] = {
                "status": bug.get("status"),         # new/assigned/fixed/verified/closed
                "assignee": bug.get("assignedTo"),
                "fix_time": bug.get("resolvedDate"),
            }
        except Exception as e:
            status_map[bug_id] = {"error": str(e)}
    return status_map
```

## 禅道配置

`.env` 中配置：

```text
ZENTAO_BASE_URL=http://your-zentao.com/zentao/api.php/v1
TEST_ZENTAO_URL=          # 可选，按环境隔离
STAGING_ZENTAO_URL=       # 可选
ZENTAO_ACCOUNT=your_account
ZENTAO_PASSWORD=your_password
```

> 注：当前 `.mcp.json` 仅启用 filesystem，Bug 提交走 SDK 直连（`utils/zentao_bug_manager.py`）。如需启用 zentao MCP server，自行实现后追加配置即可（参考 .mcp.json `_comment` 字段）。

## 提交后输出示例

```text
=== Bug 提交结果 ===
已提交：3 个 Bug

Bug#1024（P0，severity=1）：登录模块-正确密码后跳转 404
  → 已指派给：frontend-lead
  → 状态：新建

Bug#1025（P1，severity=2）：密码重置邮件发送失败
  → 已指派给：backend-dev
  → 状态：新建

Bug#1026（P2，severity=3）：用户头像上传提示文案错误
  → 已指派给：frontend-dev
  → 状态：新建

⚠️ P0 Bug 告警：存在 1 个 P0 Bug（Bug#1024），请立即关注！
```
