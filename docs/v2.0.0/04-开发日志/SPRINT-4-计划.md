# Sprint 4 计划 — B端/C端分化

> 日期: 2026-06-21
> 协议: §五-A Sprint 4
> 状态: 🔧 执行中

## 验收标准

- 🤖 tagent config set mode=enterprise → 启动后要求SSO登录
- 🤖 tagent config set mode=community → 启动后跳过SSO
- 🤖 B端RBAC: admin可管理用户 / viewer只读
- 🤖 B端审计日志: 记录登录/操作/测试执行
- 🤖 C端一键安装: brew/npm/pip/scoop全部可用
- 👤 B端真实OIDC Provider对接 (Keycloak)
- 👤 Web Dashboard浏览器渲染正常

## 现有基础盘点

| 功能 | 模块 | 状态 |
|------|------|------|
| 模式切换 | config/settings.py mode字段 | 待验证 |
| SSO OIDC | api/auth/sso.py | 待验证 |
| RBAC | api/auth/rbac.py | 待验证 |
| 审计日志 | observability/audit.py | 待验证 |
| Web Dashboard | web/ 目录 | 待验证 |
| C端安装 | brew ✅ pip ✅ npm ✅ scoop ❌ | scoop待补 |

## 任务

| # | 功能 | TDD | 预计 |
|---|------|-----|------|
| 4.1 | mode切换验证+增强 | ⬜ | enterprise/community模式隔离 |
| 4.2 | SSO OIDC集成 | ⬜ | OIDC Provider对接 |
| 4.3 | RBAC权限 | ⬜ | admin/viewer角色 |
| 4.4 | 审计日志 | ⬜ | 登录/操作/测试事件 |
| 4.5 | Web Dashboard启动 | ⬜ | 轻量版 |
| 4.6 | Scoop manifest | ⬜ | Windows包管理器 |
| 4.7 | C端安装验证 | ⬜ | 4种包管理器全链路 |
