"""
BDD（Behavior-Driven Development）/ 验收测试 - pytest-bdd 包装
被引用方：03-用例设计 + 06-自动化脚本（验收测试场景）

依赖：pip install pytest-bdd
原则：用 Gherkin（Given/When/Then）描述业务场景，业务/产品也能读懂。
"""
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


# ===== Gherkin 模板 =====

FEATURE_TEMPLATE = """# language: zh-CN
功能: {feature_name}
  作为 {role}
  我想 {action}
  以便 {benefit}

  背景:
    假设 {background_condition}

  场景: {scenario_name}
    假设 {given}
    当 {when}
    那么 {then}

  场景大纲: {scenario_outline_name}
    假设 用户 <user> 已登录
    当 输入金额 <amount>
    那么 显示结果 <result>

    例子:
      | user  | amount | result |
      | alice | 100    | OK     |
      | bob   | -1     | ERROR  |
"""


def create_feature_file(feature_name: str, scenarios: List[Dict],
                        output_dir: str = "workspace/自动化脚本/python/features") -> str:
    """生成 .feature 文件骨架"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = feature_name.replace(" ", "_").replace("/", "_")
    path = Path(output_dir) / f"{safe_name}.feature"

    lines = ["# language: zh-CN", f"功能: {feature_name}", ""]
    for s in scenarios:
        lines.append(f"  场景: {s['name']}")
        if "given" in s:
            lines.append(f"    假设 {s['given']}")
        if "when" in s:
            lines.append(f"    当 {s['when']}")
        if "then" in s:
            lines.append(f"    那么 {s['then']}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"feature 文件已生成: {path}")
    return str(path)


# ===== Step 定义模板 =====

STEP_PY_TEMPLATE = '''"""
Step 定义 - pytest-bdd 风格
对应 features/{feature}.feature
"""
from pytest_bdd import scenarios, given, when, then, parsers

scenarios("../features/{feature}.feature")


@given(parsers.parse("用户 {{user}} 已登录"))
def user_logged_in(user, page):
    pass  # TODO: 实现登录


@when(parsers.parse("输入金额 {{amount:d}}"))
def input_amount(amount, page):
    pass  # TODO


@then(parsers.parse("显示结果 {{result}}"))
def assert_result(result, page):
    pass  # TODO assert
'''


def create_step_file(feature_name: str,
                     output_dir: str = "workspace/自动化脚本/python/tests/bdd") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    safe_name = feature_name.replace(" ", "_").replace("/", "_")
    path = Path(output_dir) / f"test_{safe_name}.py"
    path.write_text(STEP_PY_TEMPLATE.format(feature=safe_name), encoding="utf-8")
    return str(path)


# ===== 验收测试质量门禁 =====

UAT_GATES = {
    "min_feature_coverage_pct": 100,    # 所有 user story 都有 .feature
    "min_step_implemented_pct": 95,     # ≥95% step 已实现
}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="BDD/UAT 工具")
    sub = parser.add_subparsers(dest="cmd")
    f = sub.add_parser("feature"); f.add_argument("name")
    s = sub.add_parser("steps"); s.add_argument("name")
    args = parser.parse_args()
    if args.cmd == "feature":
        create_feature_file(args.name, [
            {"name": "正常流程", "given": "用户已登录", "when": "执行操作", "then": "成功"}
        ])
    elif args.cmd == "steps":
        create_step_file(args.name)
