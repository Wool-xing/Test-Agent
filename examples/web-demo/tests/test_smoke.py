# SPDX-License-Identifier: MIT
"""
P0 冒烟用例最小示例。
演示：pytest fixture 注入 + Page Object 调用 + 断言。
完整 Test-Agent 工作流的 P0 冒烟门禁见 skills/smoke-test.md（≥95% 通过率）。
"""
import sys
from pathlib import Path

# 让 demo 独立可运行（不要求项目根 conftest 在 PYTHONPATH）
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pages.playwright_page import PlaywrightHomePage


@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.ui
def test_homepage_title(page):
    """TC-DEMO-UI-001: Playwright 官网首页标题包含 'Playwright'"""
    home = PlaywrightHomePage(page).goto()
    title = home.title()
    assert "Playwright" in title, f"标题异常: {title}"


@pytest.mark.p0
@pytest.mark.smoke
@pytest.mark.ui
def test_get_started_link_present(page):
    """TC-DEMO-UI-002: 首页含 Get started 链接（hero CTA）"""
    home = PlaywrightHomePage(page).goto()
    assert home.has_get_started_link(), "Get started 链接缺失"
