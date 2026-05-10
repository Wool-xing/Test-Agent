# SPDX-License-Identifier: MIT
"""
Web Demo 最小 conftest.py
仅含 Playwright browser/page fixture，演示 Page Object 模式接入。
完整 Test-Agent 工作流 conftest 见 04-配置文件/conftest.py（含 EnvConfig / api_client / cleanup_tracker / 失败截图 hook 等）。
"""
import os
import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    """Session 级 Chromium 浏览器，跨用例复用以加速。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=os.getenv("HEADLESS", "true").lower() == "true",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Function 级 page，每用例独立避免状态污染。"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
    )
    context.set_default_timeout(15000)
    p = context.new_page()
    yield p
    p.close()
    context.close()
