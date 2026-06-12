---
name: security-review
description: "代码安全审查 Skill(非渗透 layer)。每 PR/feature 必跑;OWASP Top 10 5 维自检 + SAST + 凭据检测 + 依赖 CVE。派生自 ECC security-review;补 pentest-* 层之前的源码层安全。"
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: script
---

# security-review

## 与 pentest-* 的区别(避免重复)

| Skill | 时机 | 层 |
|-------|------|----|
| **security-review**(本) | 每 PR / feature 阶段 | **代码层**(白盒静态) |
| `/pentest-coordinator` | 完整渗透项目 | **应用层**(动态利用) |
| `/pentest-vuln` | 渗透中漏洞发现 | 5 攻击域 |

本 skill = **代码 review 时安全角度**,不真打 PoC。

## 触发

- 每 PR(自动)
- 新 endpoint / 新依赖
- merge 到 main 前
- release 前

## 5 维自检(快速版)

| 维 | 检查 |
|----|------|
| **凭据** | 硬编码 password / API key / token → `gitleaks` + `truffleHog` |
| **注入** | 字符串拼接 SQL / shell / template / LDAP → grep `f"{...}"` 在 `cursor.execute` / `subprocess.run` 等 |
| **权限** | 缺 `@requires_auth` / 缺 `is_owner` 检查 → 静态扫 endpoint 装饰器 |
| **CORS / Headers** | `Access-Control-Allow-Origin: *` + 缺 CSP / X-Frame-Options 等 |
| **依赖 CVE** | `pip-audit` / `safety` / Trivy / DependencyCheck |

## 工具(本项目已有)

- `utils/security_scanner.py`(已有 67 代码示例之一)
- `bandit`(Python SAST)
- `gitleaks`(已在 pre-commit)
- `pip-audit` + `safety`

## 命令

```bash
bandit -r runtime/ -ll
gitleaks detect --source . --no-banner
pip-audit
safety check
```

## 与融合

- Shift-Left 7 层:本 skill 是 L4 pre-commit + L5 PR gate + L6 静态分析
- 渗透 PoC-only 哲学:本 skill 报 unverified 候选;喂 `/pentest-vuln` 验证

## 不做

- 不真打 PoC(留给 `/pentest-*`)
- 不修改代码("说出问题,让作者修")
- 不忽略低 severity(P3 也归档)
