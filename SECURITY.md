# 安全策略

## 支持的版本

| 版本 | 支持状态 |
|------|---------|
| 1.x  | ✅ 当前主线，持续修复安全漏洞 |
| < 1.0 | ❌ 不再维护，请升级至 1.x |

## 报告漏洞

发现安全漏洞？**请勿在公开 Issue 提交**。

### 推荐流程

1. **GitHub Security Advisories**（推荐）
   - 访问：[Security Advisories](https://github.com/Wool-xing/Test-Agent/security/advisories/new)
   - 私有提交，仅维护者可见
   - 修复后协调披露

2. **邮件**（暂未公开专用邮箱）
   - 优先使用上方 GitHub Security Advisories 私密通道
   - 如需另行联系，请通过仓库 Issue 留言索取邮件地址（不要在 Issue 中粘贴漏洞细节）
   - 标题约定：`[SECURITY] 漏洞简述`
   - 正文：详细复现步骤 + 影响范围 + PoC（如有）

### 响应时间

| 严重级别 | 响应 | 修复 |
|---------|------|------|
| Critical（RCE / 凭证泄漏） | 24h 内 | 7d 内 |
| High（数据泄漏 / 越权） | 3d 内 | 14d 内 |
| Medium（拒绝服务 / 信息泄漏） | 7d 内 | 30d 内 |
| Low（最佳实践 / 配置） | 14d 内 | 下版本 |

## 已知安全实践

本项目已内建：

- ✅ **依赖 CVE 扫描**：`pip-audit` + `safety` 在 CI 自动跑
- ✅ **Dependabot 周扫描**：每周一自动检测 + PR 升级
- ✅ **私有源 MD 隔离**：`.gitignore` 排除归属源文档
- ✅ **凭证保护**：
  - `.env` 严禁提交（`.gitignore` 排除）
  - GitHub Secrets 加密存储
  - utils 中无硬编码凭证
- ✅ **HTTPS-only**：所有 API 调用强制 TLS（utils.api_retry_util）
- ✅ **SQL 注入防护**：utils.data_factory 用 SQLAlchemy ORM，禁拼字符串
- ✅ **依赖 SAST**：bandit 扫 utils/ 自身代码

## 用户责任

部署本项目后，**用户须**：

- [ ] 将 `.env` 加入 `.gitignore`（默认已配）
- [ ] 不在 PR / Issue 贴真实凭证、token、API key
- [ ] 启用 GitHub Settings → Secret scanning（仅 Public 仓库）
- [ ] 定期 review Dependabot PR（每周一开 PR）
- [ ] 测试数据脱敏（utils.data_masking.DataMasker.mask_dict）
- [ ] 生产数据**严禁**用于测试
- [ ] 移动 APP 测试不内置生产证书 / API key

## 漏洞披露后

- CVE 编号申请（如适用）
- CHANGELOG 标注修复
- 通过 GitHub Security Advisory 公开（修复发布后）
- 致谢报告者（除非要求匿名）

## 不在范围内

以下不视为漏洞：

- 文档错别字 → 提 Issue / PR
- UI 排版问题 → 提 Issue
- 第三方依赖的已知 CVE（用 `pip-audit` 自查 + Dependabot 自动 PR）
- 测试用例失败 → 提 Issue 加 `bug` 标签
