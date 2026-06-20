# 安全策略

> 对标: Hermes Agent Security Policy

## 信任边界

**唯一的安全边界是操作系统级别隔离。** Agent进程内的任何组件——审批门、输出编辑、模式扫描器(`injection_scan.py`)、工具白名单——都不是真正的安全边界。它们是启发式方法，操作在攻击者可影响的字符串上。

Test-Agent当前的安全层次:

| 层 | 组件 | 类型 | 说明 |
|---|------|------|------|
| 1 | `safety.py` (6个gate) | 启发式 | tagent.yml显式授权检查 |
| 2 | `injection_scan.py` (8个正则) | 启发式 | prompt注入模式匹配 |
| 3 | `gateway/base.py is_safe_webhook_url` | 网络 | SSRF防护(阻止内网地址) |
| 4 | `evidence_vault _validate_evidence_path` | 文件系统 | 路径遍历防护 |
| 5 | `pentest-tester` 沙箱规则 | 文档 | Docker/VM沙箱要求(未强制执行) |

**诚实声明**: 第1-4层是合理的纵深防御启发式，但第5层(Docker沙箱)尚未在代码中强制执行。渗透测试agent目前仅生成计划文本，不执行实际攻击。在实现OS级隔离前，**不应在不可信代码/目标上运行破坏性测试命令**。

## 支持的版本

| 版本 | 支持状态 |
| ------ | --------- |
| 1.x  | ✅ 当前主线，持续修复安全漏洞 |
| < 1.0 | ❌ 不再维护，请升级至 1.x |

## 报告漏洞

发现安全漏洞？**请勿在公开 Issue 提交**。

### 推荐流程

1.**GitHub Security Advisories**（推荐）

   - 访问：[Security Advisories](https://github.com/Wool-xing/Test-Agent/security/advisories/new)
   - 私有提交，仅维护者可见
   - 修复后协调披露

2.**邮件**（暂未公开专用邮箱）

   - 优先使用上方 GitHub Security Advisories 私密通道
   - 如需另行联系，请通过仓库 Issue 留言索取邮件地址（不要在 Issue 中粘贴漏洞细节）
   - 标题约定：`[SECURITY] 漏洞简述`
   - 正文：详细复现步骤 + 影响范围 + PoC（如有）

### 响应时间（best-effort，志愿者维护）

| 严重级别 | 响应 | 修复 |
| --------- | ------ | ------ |
| Critical（RCE / 凭证泄漏） | 24h 内 | 7d 内 |
| High（数据泄漏 / 越权） | 3d 内 | 14d 内 |
| Medium（拒绝服务 / 信息泄漏） | 7d 内 | 30d 内 |
| Low（最佳实践 / 配置） | 14d 内 | 下版本 |

## 已知安全实践

本项目已内建：

- ✅**依赖 CVE 扫描**：`pip-audit` + `safety` 在 CI 自动跑
- ✅**Dependabot 周扫描**：每周一自动检测 + PR 升级
- ✅**敏感文档隔离**：`.gitignore` 排除归属源文档
- ✅**凭证保护**：
  - `.env` 严禁提交（`.gitignore` 排除）
  - GitHub Secrets 加密存储
  - utils 中无硬编码凭证

- ✅**HTTPS-only**：所有 API 调用强制 TLS（utils.api_retry_util）
- ✅**SQL 注入防护**：utils.data_factory 用 SQLAlchemy ORM，禁拼字符串
- ✅**依赖 SAST**：bandit 扫 utils/ 自身代码

## 沙箱执行层级 (对标 Codex sandbox + Hermes terminal-backend)

| 层级 | 模式 | 允许 | 禁止 | 适用场景 |
|------|------|------|------|---------|
| **L1 · read-only** | `TAGENT_SANDBOX=read` | Read/Grep/Glob | Write/Edit/Bash(写) | Plan模式, 代码审查, 需求分析 |
| **L2 · workspace-write** | `TAGENT_SANDBOX=workspace` | L1 + workspace目录写 | 外部路径写, 网络调用 | 测试生成, 报告输出 (默认) |
| **L3 · danger-full** | `TAGENT_SANDBOX=full` | L2 + 网络 + 子进程 | `rm -rf /`, `DROP TABLE` (hardline blocklist) | E2E测试, 渗透测试 (需显式授权) |

**hardline blocklist** (对标 Hermes, 所有层级生效):
- `rm -rf /` `dd if=` `mkfs.` fork bomb `:(){ :|:& };:`
- `DROP TABLE` `TRUNCATE` (数据库破坏)
- `curl` 到内网地址 (SSRF防护)
- 覆盖 `.git/` `.env` `deploy/` (受保护路径)

**当前实施状态**:
- L1/L2/L3 模式定义: ✅ (本文档)
- hardline blocklist: ⚠️ 部分 (`injection_scan.py` 8个正则)
- 受保护路径: ⚠️ 部分 (`.env` `.git` 在 `.gitignore`)
- OS级Docker隔离: ⬜ 未实现 (见信任边界声明)

## 用户责任

部署本项目后，**用户须**：

- [ ] 将 `.env` 加入 `.gitignore`（默认已配）
- [ ] 不在 PR / Issue 贴真实凭证、token、API key
- [ ] 启用 GitHub Settings → Secret scanning（仅 Public 仓库）
- [ ] 定期 review Dependabot PR（每周一开 PR）
- [ ] 测试数据脱敏（utils.data_masking.DataMasker.mask_dict）
- [ ] 生产数据**严禁**用于测试
- [ ] 移动 APP 测试不内置生产证书 / API key

## 武器化代码使用边界

本项目含**攻击面工具**示例,运行前必须取得目标系统**书面授权**:

| 资产 | 类型 |
| ------ | ------ |
| `agents/15-渗透测试.md` | 渗透测试 Agent(调用 sqlmap / Metasploit / Hydra 等真实攻击工具) |
| `skills/pentest-*.md`(7 项) | 渗透 skill 系列(api / coordinator / exploit / recon / report / vuln / web) |
| `utils/api_security_scanner.py` | API 安全扫描器(SSRF / IDOR / JWT / CSRF; 默认 refuse,需 `TAGENT_PENTEST_AUTHORIZED=1` + AWS metadata 探针需 `confirm_metadata_probe=True`) |
| `utils/ai_adversarial.py` | AI 对抗测试 / LLM 越狱 / Prompt Injection / 成员推断攻击(含 JAILBREAK_PROMPTS + PROMPT_INJECTION_TEMPLATES 模板; 4 个远端 op 默认 refuse,需 `TAGENT_PENTEST_AUTHORIZED=1`; `test_llm_jailbreak` / `test_prompt_injection` / `membership_inference_basic` 三个 HIGH 风险 op 额外需 `confirm_offensive=True` 或 `confirm_inference_attack=True` kwarg) |
| `utils/security_scanner.py` | 通用安全扫描器(调用 ZAP / Burp) |

**操作者必须**:

- [ ] 仅在**自己拥有 / 经书面授权**的系统上运行上述工具
- [ ] 在 `tagent.yml` 显式设置 `pentest.authorized: true`(此为操作者自证授权,不构成第三方授权证明)
- [ ] 遵守所在司法管辖区法律:
  -**中国**:《刑法》§285-§287(非法侵入 / 破坏 / 非法控制计算机信息系统罪);《网络安全法》§27 /
  -**美国**:Computer Fraud and Abuse Act(CFAA, 18 U.S.C.)
  -**欧盟**:NIS2 Directive(EU 2022/2555)

**项目维护者免责**:本项目以 MIT License 提供"原样"代码。误用即攻击;由操作者承担**全部**法律责任,项目维护者不承担连带责任。

## 测试工具准入控制(utils env-var gate)

本项目 utils 中部分函数具有**副作用 / 命令注入面 / 任意 SQL 执行**(非武器化攻击工具,但误调同样损坏环境)。默认 refuse,需对应环境变量授权:

| utils 文件 | env var | 守护操作 | 额外约束 |
| ------ | ------ | ------ | ------ |
| `utils/chaos_helper.py` | `TAGENT_CHAOS_AUTHORIZED=1` | 混沌注入 + path / host validation | – |
| `utils/db_test_helper.py` | `TAGENT_DB_TEST_AUTHORIZED=1` | `explain_query` / `benchmark_query` / `test_migration` / `test_postgres_backup_restore` | `test_postgres_backup_restore` 额外需 `confirm_destructive=True` kwarg;SQL identifier + cmd 双白名单 |
| `utils/desktop_driver.py` | `TAGENT_DESKTOP_AUTHORIZED=1`(仅 macOS ops) | macOS: `open_macos_app` / `macos_menu`;跨平台: `get_windows_app` / `launch_electron` 路径校验 | macOS ops 需 platform=darwin + AppleScript identifier 白名单;跨平台 driver 接受的 exe / executable 路径必须绝对 + 存在 + 普通文件 + 非 symlink |

**与武器化代码区分**: 上述 utils 设计用途是**测试**而非**攻击**,但调用时仍执行任意 SQL / shell / AppleScript。env var gate 是误调防护,不豁免操作者的环境隔离责任。

**授权范围**: 仅 dedicated 测试库 / 自有 macOS 测试机 / 隔离环境。生产严禁。

**实现 PR**: chaos_helper #37 / db_test_helper #41 / desktop_driver #44(范式: env gate + opt-in kwarg + platform gate + 输入白名单)。

## 上游归属与思想-表达分离

针对 `NOTICE.md` 列出的上游条目(尤其上游无 LICENSE 文件 / AGPL 等):

本项目所摘均为**抽象架构观察 / 设计模式 / 工程思想**,不复用上游源代码字面值、字符串常量、API 签名或专有数据结构(idea-expression dichotomy)。

如发现疑似复用,请通过 GitHub Security Advisories 私密通道告知,**立即移除**。

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
