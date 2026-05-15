---
name: e2e-testing
description: "E2E 测试 Skill。Playwright 关键用户流 + 跨浏览器 + 2FA/TOTP/SSO 自动登录 + 视觉回归 + 录屏。派生自 ECC e2e-testing(主宪章 §28)。"
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# e2e-testing

## 触发

- 任何用户可见功能
- 关键 user journey(登录 / 支付 / 创建 / 删除)
- 跨浏览器兼容验证
- 视觉回归

## 关键设计

| 维度 | 实现 |
|------|------|
| 浏览器 | Playwright(Chromium / Firefox / WebKit) |
| 2FA / TOTP | `pyotp.TOTP(SECRET).now()` |
| SSO | Playwright follow redirects(Okta / Auth0 / Azure AD / Keycloak) |
| 视觉回归 | `screenshot()` + SSIM(主宪章 §21 测试类型) |
| 录屏 | `context = browser.new_context(record_video_dir="evidence/")`|
| Trace | `tracing.start(screenshots=True, snapshots=True)` |

## Page Object 模式(必)

```python
class LoginPage:
    def __init__(self, page):
        self.page = page

    def login(self, user, pwd):
        self.page.fill('input[name=email]', user)
        self.page.fill('input[name=password]', pwd)
        self.page.click('button[type=submit]')
```

## 关键用户流必测(模板)

1. 注册 + 邮箱验证
2. 登录(含 2FA / SSO)
3. 找回密码
4. 核心业务(下单 / 创建 / 编辑 / 删除)
5. 退出 + 登录失效
6. 错误路径(密码错 5 次锁定 等)

## 与主宪章融合

- §17 测试架构:E2E 占金字塔顶层 10%
- §21 测试类型:含视觉回归
- §21 横切可复现性:trace + 录屏 + screenshots
- §22 6-缺陷 RCA(回归 + 变更影响)

## 不做

- 不测试每个像素(用 SSIM,留容差)
- 不在 E2E 跑业务单元验证(留 unit/integration 层)
- 不无头不录屏(失败必有录屏证据)
