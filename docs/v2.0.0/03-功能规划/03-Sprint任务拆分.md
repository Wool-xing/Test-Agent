# V2.0.0 Sprint 任务拆分

> **日期:** 2026-06-20
> **原则:** 每个Sprint = 1周；每Sprint结束必须通过质量门禁（§七）
> **弹性:** Sprint可延期，质量门禁不可妥协（§零-C优先级链）

---

## Sprint 0：地基（屎山清理 + 基础设施）

**目标:** 审计修复 + 项目骨架就绪 + `tagent --version`可运行

| 任务 | 粒度 | 验收 | P0-ID |
|------|------|------|------|
| 拆分 slash_handlers.py → handlers/core.py + handlers/task.py + handlers/cron.py | 4h | 3文件各≤800行，测试通过 | P0-001 |
| 拆分 interactive.py → interactive.py + tui/render.py | 3h | ≤800行 | P0-002 |
| 分解 run_decision_direct() CC=42→≤15 | 4h | 5-6个子函数，CC均≤15 | P0-003 |
| 分解 execute_node() CC=28→≤15 | 3h | 4-5个子函数 | P0-004 |
| 分解 analyze() + parse() + _cmd_task() + register/demo + extract_text | 5h | 5个函数CC≤15 | P0-005~009 |
| 填充11空壳函数（defect_tracker + agents/base + exporters/base + backends） | 3h | NotImplementError或实际实现 | P0-007 |
| 修复 skills.registry 导入 | 0.5h | import通过 | P0-008 |
| 清理未使用导入 + 孤立节点确认 | 2h | 0未使用导入 | P0-009 |
| 目录结构重组（core/agent/infra/ui/） | 4h | §补-26规范 | P0-010 |
| Config系统（5层优先级: CLI>Env>Project>User>Default） | 3h | tagent config get/set | P0-011 |
| Logger（结构化JSON + Trace ID + 脱敏） | 2h | JSON日志输出 | P0-012 |
| CLI框架就绪（Typer: tagent --help/--version） | 1h | 可执行 | P0-013 |
| pytest配置 + coverage基线 | 1h | pytest --cov | P0-014 |
| .gitignore + pre-commit hooks | 1h | 无垃圾文件入仓 | P0-016 |
| 全量测试通过（修复后） | 2h | 650测试全PASS | - |

**Sprint 0 门禁:**
- [ ] `tagent --help` 输出完整
- [ ] 0文件>800行，0函数CC>20
- [ ] 全量测试通过，覆盖率不下降
- [ ] 3平台构建通过

---

## Sprint 1：最小可用

**目标:** 用户安装→初始化→自然语言描述测试→看到彩色结果，<5分钟

| 任务 | 粒度 | P0-ID |
|------|------|------|
| tagent init — 初始化测试项目 | 3h | P0-017 |
| tagent run — 自然语言执行测试 | 4h | P0-018 |
| tagent chat — REPL对话模式 (prompt_toolkit+Rich) | 5h | P0-019 |
| tagent report — Rich彩色报告 | 2h | P0-020 |
| 5个内置Skill: ping/http/file/process/timeout | 5h | P0-021 |
| 一键安装脚本（install.sh/ps1） | 3h | P0-022 |
| MCP Server基础集成 | 3h | P0-023 |
| 首次使用引导 (Onboarding wizard) | 3h | P0-024 |
| 沙箱执行（级别1: 进程隔离） | 4h | P0-025 |

**Sprint 1 门禁:**
- [ ] 新用户5分钟: 安装→初始化→自然语言测试→彩色报告
- [ ] 3平台安装验证通过

---

## Sprint 2：Agent核心 + Chat TUI

**目标:** Agent自主执行测试 + prompt_toolkit+Rich对话体验

| 任务 | 粒度 | P1-ID |
|------|------|------|
| 主Agent引擎（LLM驱动自然语言理解） | 5h | P1-001 |
| 工具系统（Read/Write/Shell/Network/MCP） | 4h | P1-002 |
| Hook系统（10+事件类型） | 4h | P1-003 |
| 权限系统（3级allow/deny/ask） | 3h | P1-004 |
| Chat TUI（prompt_toolkit输入+Rich渲染） | 5h | P1-005 |
| LLM成本管控（Token预算+预估+降级） | 3h | P1-010 |
| 多LLM Provider（Claude/GPT/Gemini/Ollama/DeepSeek） | 3h | P1-040 |

---

## Sprint 2-A：Dashboard TUI

**目标:** Textual 10面板全功能可用

| 任务 | 粒度 | P1-ID |
|------|------|------|
| TUI框架搭建（Textual App + 面板路由） | 3h | P1-006 |
| 对话主界面 + 执行面板 | 3h | P1-006 |
| 报告仪表盘 + Skill浏览器 | 3h | P1-006 |
| 配置编辑器 + 日志查看器 | 3h | P1-006 |
| 任务调度面板 + Agent状态页 | 2h | P1-006 |
| 帮助/教程 + 皮肤选择器 | 2h | P1-006 |
| 3套主题 + 响应式 + 虚拟滚动 | 3h | P1-007~009 |

---

## Sprint 3：扩展体系

| 任务 | 粒度 | P1-ID |
|------|------|------|
| Skill SDK + SKILL.md模板 | 5h | P1-011/015 |
| Skill注册与发现（本地+远程） | 4h | P1-012 |
| Skill市场 | 4h | P1-013 |
| Plugin系统 | 3h | P1-014 |
| Skill权限声明 + 签名验证 | 4h | P1-016 |

---

## Sprint 4：B端/C端 分化

| 任务 | 粒度 | P1-ID |
|------|------|------|
| 模式切换（enterprise/community） | 2h | P1-017 |
| B端: SSO + RBAC + 审计 | 8h | P1-018~020 |
| C端: 一键安装全平台 | 3h | P1-021 |
| Web Dashboard（React+Vite） | 6h | P1-022 |
| Web Dashboard安全（§补-33） | 4h | P1-023 |
| API Server安全（§补-34） | 4h | P1-024 |
| 多租户数据隔离 | 5h | P1-025 |

---

## Sprint 5：测试能力全覆盖

| 任务 | 粒度 | P1-ID |
|------|------|------|
| 单元测试 + 集成测试执行器 | 5h | P1-026/027 |
| Cypress引擎集成（组件测试+前端E2E） | 5h | P1-028 |
| Playwright引擎集成（跨浏览器+视觉+API） | 5h | P1-029 |
| 渗透测试 + 视觉回归 + 移动端测试 | 8h | P1-030~032 |
| 定时任务调度（Cron + 重试 + DLQ） | 5h | P1-033 |
| 并行执行架构（Worker Pool 100并发<60s） | 6h | P1-034 |
| 测试数据管理 + 非确定性测试策略 | 4h | P1-035/036 |
| 自测闭环 + 故障演练 | 4h | P1-037/038 |

---

## Sprint 6：企业级完善

| 任务 | 粒度 | P2-ID |
|------|------|------|
| 报告系统（HTML/PDF/JSON/JUnit） | 4h | P2-001 |
| 通知系统（5+渠道） | 4h | P2-002 |
| 知识图谱集成 | 3h | P2-003 |
| 性能优化（补-12 14项达标） | 6h | P2-004 |
| Feature Flag + 灰度发布 | 3h | P2-005 |
| 依赖安全审计 + SBOM | 2h | P2-006 |
| 遥测 + 离线模式 | 4h | P2-007/008 |
| 文档-代码一致性检查 | 2h | P2-009 |
| 废弃策略 + i18n + 无障碍 | 5h | P2-010~012 |
| API版本化 + 自动更新 | 3h | P2-013/014 |
| DI + Fake实现 | 3h | P2-015 |

---

## Sprint 7：发布准备

| 任务 | 粒度 | P2-ID |
|------|------|------|
| 多平台包构建（Win/Mac/Linux/Docker） | 5h | P2-016 |
| 部署回滚策略 | 2h | P2-017 |
| 用户文档（README/快速开始/用户指南/API） | 5h | P2-018 |
| 开发者文档 | 3h | P2-019 |
| CHANGELOG + Release Notes | 2h | P2-020 |
| 开源合规（LICENSE/SBOM/CONTRIBUTING） | 2h | P2-021 |
| 社区治理（GOVERNANCE/MAINTAINERS） | 2h | P2-022 |
| CI/CD全流水线（§八-B 6阶段） | 4h | P2-023 |
| GitHub Release + 全平台分发 | 3h | P2-024 |
| 部署冒烟测试（全链路） | 3h | P2-025 |

---

## Sprint 8：IM远程交互（可选）

| 任务 | 粒度 | P3-ID |
|------|------|------|
| IM Bot适配层（企微/飞书/钉钉） | 5h | P3-001 |
| 消息路由 | 3h | P3-002 |
| 权限控制 + 会话隔离 | 3h | P3-003/004 |
| 移动端APK/IPA（最小可用版） | 5h | P3-005 |

---

## 周级时间线

```
Week 0:  Sprint 0  ████████ 地基
Week 1:  Sprint 1  ████████ 最小可用
Week 2:  Sprint 2  ████████ Agent核心 + Chat TUI
Week 2.5: Sprint 2A ██████  Dashboard TUI
Week 3:  Sprint 3  ████████ 扩展体系
Week 4:  Sprint 4  ████████ B/C分化
Week 5-6: Sprint 5 ██████████████ 测试全覆盖
Week 7-8: Sprint 6 ██████████████ 企业级
Week 9:  Sprint 7  ████████ 发布
Week 10: Sprint 8  ████████ IM Bot (可选)
```

---

*Sprint拆分完成: 2026-06-20*
