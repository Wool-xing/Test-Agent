## 目标

修复 PR #145 (release/v1.43.0) 上 pytest 单元 13 fail。三件套：A 合 main、B 装依赖、C 调断言。

## 改动

**A — merge main（拿 markdown 修复 PR #146）**
- `docs/charter/07-runtime-license.md`：解决 conflict，保留 release 分支语义（V1.36.0 / 16 skill rollout）+ 采用 main 的 `../../` 链接路径
- 三个 doc 文件（SURVEY/charter/demo recipe）来自 PR #146 自动合入

**B — `defusedxml` 缺失**
- `.github/workflows/ci.yml` line 342（L7 selftest-mock job）+ line 371（pytest-unit job）补 `defusedxml`
- `config/requirements.txt`：新增 `defusedxml==0.7.1`（XXE/亿笑/decompression bomb 防护）

**C — `test_impl_status_filter.py` 适配 V1.43.0**
- `test_registry_skill_status_counts`：production 23→25、vision 2→0（V1.43.0 把 2 个 ex-vision skill 实装为 production）
- `test_router_flags_vision_skill` + `test_execute_node_rejects_vision_skill`：vision 分支与 rollout 共用同一 hard-block 路径，catalog 现无 vision skill，改用 `phantom-vision-skill` (unknown) 触发同分支，保留覆盖语义。沿用 V1.20 rollout-收尾时同样的占位模式

## 本地验证

```
pytest runtime/tests/test_impl_status_filter.py -p no:cacheprovider
→ 13 passed in 1.21s
```

## 不在本 PR 范围

- **D**: `test_utils_bug_tracker.py::test_zentao_registered` — zentao tracker 未注册（V1.x 遗留功能性 debt）
- **E**: L2 selftest · mock LLM e2e — utils-reorg 后路径丢失（utils/excel_generator.py / data_factory.py / generate_report.py）

这两项与 V1.43.0 release 无关，下一轮单开 PR。

## 落地后

PR #145 (release/v1.43.0) CI 由 3 失败 → 应只剩 CodeQL setup 4s 失败（pre-existing CodeQL config 问题）。届时可考虑合并 #145。
