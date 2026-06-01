## 目标

收 PR #145 上剩余 3 项 CI debt（D + E + CodeQL 诊断）。

## 改动

### D — `test_zentao_registered` FAIL

**根因**：`utils/trackers/zentao_bug_manager.py:14` 用 `from utils.protocols.api_retry_util import call_with_retry` —— 绝对包路径。CI pytest 把 `utils/` 插到 `sys.path`（不含项目根），所以 `utils.protocols` 包名解析失败 → ImportError → `bug_tracker_base.py` 的 try/except 静默吞掉 → `TRACKER_REGISTRY` 缺 `zentao`。其余 4 个 tracker (`github` / `jira` / `linear` / `webhook`) 用 `from bug_tracker_base import ...` 同包风格不受影响。

**修复**：加 fallback：
```python
try:
    from utils.protocols.api_retry_util import call_with_retry
except ImportError:
    from protocols.api_retry_util import call_with_retry
```

**本地验证**：`test_utils_bug_tracker.py` 11/11 passed。

### E — L2 selftest 3 个 DAG 节点 "script not found under utils/"

**根因**：V1.x utils-reorg 把脚本移进子目录：
- `excel_generator.py` → `utils/reporting/`
- `data_factory.py` → `utils/data/`
- `generate_report.py` → `utils/reporting/`

但 `runtime/orchestrator/adapters/scripts.py` 的 `run_script` 和 `list_available_scripts` 只查 `scripts_dir.glob("*.py")` —— top-level 扁平查找，找不到子目录里的脚本。

**修复**：改成 `rglob("*.py")` 递归，basename 唯一时自动解析子目录路径，多个匹配时 raise 明确错误。

**本地验证**：`python -m runtime.cli.main selftest --e2e --pass-threshold 0.80` → `✓ PASS 9/9 ok (100%, tolerant ≥80%)`。

### CodeQL — 不在本 PR 范围

**诊断**：PR #145 上的 `CodeQL` 失败（4 秒 setup fail）来自 GitHub repo 的「Default setup」CodeQL 配置，与本仓 `.github/workflows/codeql.yml`（"CodeQL Advanced"）无关 —— 后者在所有最近的 release/v1.43.0 run 上都 SUCCESS。

**需操作（GitHub UI）**：仓库 Settings → Code security → Code scanning → 关掉 "Default setup"，只保留 Advanced workflow。

## 落地后预期

PR #145 (release/v1.43.0) 应剩 0 失败（或仅剩 GitHub default-setup CodeQL，需 UI 关掉）。
