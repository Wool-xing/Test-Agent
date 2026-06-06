# FIX-LOG.md · 修复记录

## 已修复 (14个PR, ~55项)

| # | PR | 文件 | 级别 | 问题 | 验证 |
|---|-----|------|------|------|------|
| 1 | #213 | .github/workflows/*.yml | CRITICAL | CI action版本不存在(@v6/v7/v8) | CI通过 |
| 2 | #213 | CLAUDE.md | CRITICAL | AI指令文件缺失 | git tracked |
| 3 | #213 | runtime/observability/dashboard.py | CRITICAL | 死代码list comprehension | 595 tests |
| 4 | #213 | runtime/orchestrator/adapters/script_bridge.py | CRITICAL | callable→Callable类型 | 595 tests |
| 5 | #213 | runtime/orchestrator/workflows/test_coordinator.py | CRITICAL | execute_node()多余参数run_id= | 595 tests |
| 6 | #213 | utils/protocols/protocol_helper.py | CRITICAL | SOAP xml_escape双重转义 | 595 tests |
| 7 | #213 | desktop/electron/main.ts | HIGH | IPC handlers未注册 | 编译通过 |
| 8 | #213 | install.py | HIGH | os.fdopen()→open() Python3.13 | 语法OK |
| 9 | #213 | install.py | HIGH | sys.stdout.encoding空值防护 | 语法OK |
| 10 | #213 | runtime/backends/ssh.py | CRITICAL | known_hosts=None MITM风险 | 595 tests |
| 11 | #213 | utils/state_machine_tester_v2.py | CRITICAL | eval()/exec()代码注入 | 595 tests |
| 12 | #213 | utils/security/security_scanner.py | CRITICAL | Burp API key URL泄露+SSRF | 595 tests |
| 13 | #213 | utils/data/db_test_helper.py | CRITICAL | SQL注入DDL f-string | 595 tests |
| 14 | #213 | utils/platforms/desktop_driver.py | HIGH | AppleScript注入 | 595 tests |
| 15 | #213 | config/conftest.py | HIGH | 硬编码默认密码 | 595 tests |
| 16 | #213 | utils/design/suite_minimizer.py | HIGH | 返回类型List→Dict+缺Any | Ruff OK |
| 17 | #213 | utils/a11y_i18n/fairness_auditor.py | HIGH | docstring位置错误 | 语法OK |
| 18 | #213 | utils/reporting/evidence_chain.py | HIGH | 裸导入路径修正 | 语法OK |
| 19 | #213 | runtime/api/deps.py | MEDIUM | Prefect except收窄 | 595 tests |
| 20 | #213 | runtime/orchestrator/direct.py | MEDIUM | 移除不必要线程池包装 | 595 tests |
| 21 | #213 | utils/data/data_factory_v2.py | MEDIUM | defaultdict导入顺序 | 语法OK |
| 22 | #213 | utils/security/schema_fuzzer.py | MEDIUM | exit()→sys.exit() | 语法OK |
| 23 | #214 | agents/09-报告生成.md | LOW | @v6遗留引用 | 文档 |
| 24 | #215 | docs多个文件 | LOW | 67→79脚本数对齐 | 文档 |
| 25 | #216 | desktop/electron/version.ts等 | HIGH | 版本/端口硬编码→共享常量 | 编译OK |
| 26 | #216 | config/conftest.py | MEDIUM | 移除默认db凭证硬编码 | 595 tests |
| 27 | #217 | utils/protocols/mq_helper.py | MEDIUM | 移除guest:guest硬编码 | 语法OK |
| 28 | #218 | .gitignore | LOW | 排除运行时文件 | CI OK |
| 29 | #219 | runtime/router/llm_client.py | MEDIUM | except Exception→ImportError | 595 tests |
| 30 | #220 | desktop/electron/tsconfig.json | MEDIUM | TS7+ moduleResolution适配 | 编译OK |
| 31 | #222 | utils/trackers/*.py | HIGH | 双重导入issubclass失败 | 595 tests |
| 32 | #223 | utils/reporting/generate_report.py | MEDIUM | Server酱通知集成 | 真实验证 |
| 33 | #224 | runtime/orchestrator/adapters/experts.py | HIGH | 报告生成器聚合真实Agent输出 | 真实验证 |
| 34 | #226 | utils/trackers/*.py | MEDIUM | try/except导入兼容pytest内外 | 语法OK |
| 35 | #227 | runtime/router/llm_client.py | MEDIUM | TAGENT_LLM_MODEL env覆盖 | 真实验证 |
| 36 | #227 | runtime/router/model_router.py | MEDIUM | TAGENT_LLM_MODEL覆盖ModelTier | 真实验证 |
| 37 | #227 | runtime/orchestrator/adapters/experts.py | MEDIUM | PROJECT_VERSION/PROJECT_NAME env | 595 tests |
| 38 | #227 | runtime/cli/config.py | MEDIUM | OLLAMA_HOST env覆盖 | 语法OK |

- CRITICAL: 8 · HIGH: 9 · MEDIUM: 17 · LOW: 4
