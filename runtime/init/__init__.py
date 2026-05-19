"""tagent init · 配置自动组装(V1.12.0).

读 `config/templates/matrix.yaml` 矩阵 + base.*.tpl 模板,产 `.env` + `tagent.yml` + `STARTUP.md`。
矩阵 8 测试类型 × 6 平台 × 5 LLM × 6 BugTracker × 6 通知 = 8640 组合,wizard 自动列出。

主入口:
    from runtime.init.wizard import run_wizard
    answers = run_wizard()                     # 交互
    from runtime.init.renderer import render_all
    out_paths = render_all(answers, out_dir)
"""
