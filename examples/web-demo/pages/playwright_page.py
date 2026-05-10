# SPDX-License-Identifier: MIT
"""
Playwright 官网首页 Page Object 示例。
演示 Page Object 模式：
- 选择器集中（不散落在用例里）
- 页面动作封装（goto / search 等）
- 用例只调高层方法，不直接操作 selector
"""
from playwright.sync_api import Page


class PlaywrightHomePage:
    URL = "https://playwright.dev/"

    # 选择器集中（优先 role > test-id > label > text）
    GET_STARTED_LINK = 'text="Get started"'  # hero CTA，稳定多年
    HERO_TITLE = "h1"

    def __init__(self, page: Page):
        self.page = page

    def goto(self):
        self.page.goto(self.URL, wait_until="domcontentloaded")
        return self

    def title(self) -> str:
        return self.page.title()

    def hero_text(self) -> str:
        return self.page.locator(self.HERO_TITLE).first.inner_text()

    def has_get_started_link(self) -> bool:
        return self.page.locator(self.GET_STARTED_LINK).count() > 0
