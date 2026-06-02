"""Test-Agent workspace output path helpers.

All paths follow: workspace/测试报告/{PROJECT_NAME}[/{run_id}]/{sub_path}"""

import os
import uuid
from datetime import datetime
from pathlib import Path

_RUN_ID: str | None = None


def get_project_name() -> str:
    return os.getenv("PROJECT_NAME", "default")


def get_output_base(project: str | None = None) -> Path:
    if project is None:
        project = get_project_name()
    return Path("workspace/测试报告") / project


def get_output_dir(sub_path: str = "", run_id: str | None = None) -> Path:
    """workspace/测试报告/{PROJECT_NAME}[/{run_id}]/{sub_path}

    run_id=None → project-level (baselines/history/decisions)
    run_id=str  → per-run isolation (screenshots/allure-results/...)
    """
    base = get_output_base()
    if run_id:
        base = base / run_id
    return base / sub_path if sub_path else base


def current_run_id() -> str:
    global _RUN_ID
    if _RUN_ID is None:
        _RUN_ID = os.getenv("RUN_ID") or f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    return _RUN_ID
