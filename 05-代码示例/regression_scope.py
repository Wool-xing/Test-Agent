# SPDX-License-Identifier: MIT
"""
回归测试变更影响范围分析
被引用方：regression-test skill
配置：从 workspace/regression_modules.yaml 读取模块映射，无配置时使用默认 fallback。
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

DEFAULT_MODULES: Dict[str, List[str]] = {
    # 默认 fallback；项目应在 workspace/regression_modules.yaml 自定义
    "login": ["auth/", "user/login", "session/"],
    "payment": ["payment/", "order/"],
    "profile": ["user/profile", "account/"],
}


def _load_modules_config() -> Dict[str, List[str]]:
    """优先读取 workspace/regression_modules.yaml；否则用默认。"""
    cfg_path = Path("workspace/regression_modules.yaml")
    if cfg_path.exists():
        try:
            import yaml  # PyYAML
            with open(cfg_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            modules = data.get("modules", {})
            if modules:
                return modules
        except ImportError:
            logger.warning("PyYAML 未安装，使用默认 module 映射")
        except Exception as e:
            logger.warning(f"解析 regression_modules.yaml 失败: {e}")
    return DEFAULT_MODULES


def analyze_change_impact(base_branch: str = "main") -> Dict:
    """分析 git diff 的变更文件，推断受影响测试模块。"""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
            capture_output=True, text=True, check=False
        )
        changed_files = [f for f in result.stdout.strip().split("\n") if f]
    except Exception as e:
        logger.error(f"git diff 失败: {e}")
        changed_files = []

    module_patterns = _load_modules_config()
    affected = set()
    for f in changed_files:
        for module, patterns in module_patterns.items():
            if any(p in f for p in patterns):
                affected.add(module)

    max_modules = int(os.getenv("MAX_AFFECTED_MODULES_FULL_REGRESSION", "3"))
    return {
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "affected_modules": sorted(affected),
        "full_regression_needed": len(affected) > max_modules,
        "recommendation": "full" if len(affected) > max_modules else "targeted",
    }


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(analyze_change_impact(), indent=2, ensure_ascii=False))
