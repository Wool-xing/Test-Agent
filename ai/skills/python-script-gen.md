---
name: python-script-gen
description: pytest 自动化脚本生成技能。输入测试用例 Excel 或功能描述，生成可直接运行的 pytest 自动化测试脚本，支持 UI（Playwright）+ API（requests）。性能脚本主用 JMeter（见 /jmeter-script-gen），Locust 仅作开发期备用。
tools: Read, Write, Edit, Grep, Glob
SKILL_IMPL_STATUS: production
---

# Python 自动化脚本生成

## 触发方式

```text
/python-script-gen [测试用例 Excel 路径 或 功能描述]
```

## 🔔 调用前置准备

```text
□ 测试用例 Excel（workspace/测试用例/testcases_*.xlsx）或功能描述
□ pytest + pytest-playwright 已装
□ Playwright 浏览器（playwright install chromium）
□ conftest.py 已部署项目根
□ utils/api_retry_util.py 已部署（脚本会 import call_with_retry）
□ 测试目标 URL → .env TEST_APP_URL / TEST_API_URL
```

## 执行流程

### Step 1：分析用例

```text
读取 Excel 测试用例，提取：
  - 测试场景和步骤
  - 测试数据（输入/预期）
  - 用例类型（UI / API / PERF / SEC）
  - 优先级分布
```

### Step 2：生成脚本

```text
由 automation-engineer 执行：
  - 根据用例类型选择框架（Playwright / requests）
  - 性能用例 → 转交 /jmeter-script-gen
  - 生成 Page Object（UI）
  - 生成 BaseAPI/UserAPI 等封装（API）
  - 集成 utils.api_retry_util 的 call_with_retry
  - 集成项目根 conftest.py 中的 fixture
```

## 脚本类型选择

| 用例 TYPE | 生成类型 | 框架 |
|-----------|---------|------|
| UI | UI 自动化 | Playwright |
| API | API 测试 | requests + pytest |
| PERF | 性能测试 | **转交 /jmeter-script-gen**（主） |
| SEC | 安全验证 | requests + pytest（含 SQL 注入/XSS 探测） |

> 注：Locust 仅作开发期 Python 内压测备用，正式 CI/release 性能门禁以 JMeter 为准。

## 生成示例（UI）

### 输入

```text
功能：用户注册
步骤：
1. 访问注册页
2. 填写手机号、验证码、密码
3. 点击注册
4. 验证注册成功跳转
```

### 输出

```python
# workspace/自动化脚本/python/tests/test_p0_smoke/test_register_ui_p0.py
import pytest
from playwright.sync_api import Page, expect

from pages.register_page import RegisterPage


@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.register
class TestRegisterUI:

    def test_register_success_p0(self, page: Page, test_data):
        """TC-REGISTER-UI-001: 正常注册流程"""
        register = RegisterPage(page)
        register.navigate()
        register.fill_phone(test_data["new_user"]["phone"])
        register.request_sms_code()
        register.fill_sms_code(test_data["new_user"]["sms_code"])
        register.fill_password(test_data["new_user"]["password"])
        register.submit()
        expect(page).to_have_url("/home")
        expect(page.get_by_test_id("welcome-message")).to_be_visible()

    @pytest.mark.parametrize("phone,sms,pwd,error", [
        ("",            "123456", "Test@123", "请输入手机号"),
        ("13800138000", "wrong",  "Test@123", "验证码错误"),
        ("13800138000", "123456", "weak",     "密码强度不足"),
    ])
    @pytest.mark.p1
    def test_register_validation_p1(self, page, phone, sms, pwd, error):
        """TC-REGISTER-UI-002~004: 注册表单验证"""
        register = RegisterPage(page)
        register.navigate()
        register.fill_phone(phone)
        register.fill_sms_code(sms)
        register.fill_password(pwd)
        register.submit()
        assert error in register.get_error_message()
```

## 生成示例（API）

```python
# workspace/自动化脚本/python/tests/test_p0_smoke/test_login_api_p0.py
import pytest

from api.user_api import UserAPI


@pytest.fixture(scope="class")
def user_api(api_client, env_config):
    return UserAPI(api_client, env_config.api_base_url)


@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.api
@pytest.mark.login
class TestLoginAPI:

    def test_login_success_p0(self, user_api, test_data):
        """TC-LOGIN-API-001"""
        resp = user_api.login(
            test_data["normal_user"]["username"],
            test_data["normal_user"]["password"],
        )
        assert resp.status_code == 200
        assert "token" in resp.json()

    @pytest.mark.parametrize("user,pwd,code", [
        ("wrong", "any", 401),
        ("",      "any", 400),
    ])
    @pytest.mark.p1
    def test_login_errors_p1(self, user_api, user, pwd, code):
        """TC-LOGIN-API-002~003"""
        resp = user_api.login(user, pwd)
        assert resp.status_code == code
```

## 代码质量要求

```text
✅ 无硬编码数据（使用 test_data fixture）
✅ 无 time.sleep()（使用 Playwright 显式等待 / expect 自动重试）
✅ 选择器语义化（data-testid > role > label > text）
✅ API 调用经 utils.api_retry_util.call_with_retry（指数退避）
✅ 失败时有明确 assert message
✅ 每个测试方法有 docstring（含用例 ID）
✅ 参数化用 @pytest.mark.parametrize
✅ fixture scope 正确（session/class/function）
✅ marker 完整：@p0/@p1 + @smoke/@regression + @ui/@api + @{module}
```

## 输出文件结构

```text
workspace/自动化脚本/python/
├── pages/                              # UI Page Object
│   └── {module}_page.py
├── api/                                # API 封装
│   ├── base_api.py
│   └── {module}_api.py
└── tests/
    ├── test_p0_smoke/
    │   └── test_{module}_{type}_p0.py
    ├── test_p1_regression/
    │   └── test_{module}_{type}_p1.py
    └── test_p2_full/
        └── test_{module}_{type}_p2.py
```

## 脚本调试

```bash
# 语法检查（跨平台，比 shell glob 更稳）
python -m compileall workspace/自动化脚本/python/

# 运行单条用例
pytest workspace/自动化脚本/python/tests/test_p0_smoke/test_login_ui_p0.py::TestLoginUI::test_normal_login_p0 -v

# 有头模式调试 UI（Linux/Mac）
HEADLESS=false pytest workspace/自动化脚本/python/tests/test_p0_smoke/ -v

# 有头模式调试 UI（Windows PowerShell）
$env:HEADLESS="false"; pytest workspace/自动化脚本/python/tests/test_p0_smoke/ -v

# 生成 Allure 报告
pytest workspace/自动化脚本/python/tests/ \
    --alluredir=workspace/测试报告/{项目名}/allure-results -v
```
