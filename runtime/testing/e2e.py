"""E2E test executor using Playwright (Sprint 5)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class E2EConfig:
    browser: str = "chromium"
    headless: bool = True
    timeout_seconds: int = 30
    viewport_width: int = 1280
    viewport_height: int = 720


@dataclass
class E2EResult:
    status: str  # pass | fail | error
    url: str
    title: str = ""
    summary: str = ""
    checks: list[dict] = field(default_factory=list)
    error: str | None = None
    screenshot_path: str | None = None
    duration_ms: int = 0


class E2EExecutor:
    """Execute E2E tests using Playwright browser automation."""

    def __init__(self, config: E2EConfig | None = None):
        self._config = config or E2EConfig()

    def check_page(self, url: str) -> E2EResult:
        """Navigate to a URL and verify the page loads correctly.

        Checks: HTTP response OK, page title present, no console errors.
        """
        import time

        start = time.monotonic()
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = getattr(p, self._config.browser)
                ctx = browser.launch(headless=self._config.headless)
                page = ctx.new_page(
                    viewport={"width": self._config.viewport_width, "height": self._config.viewport_height}
                )
                page.set_default_timeout(self._config.timeout_seconds * 1000)

                errors: list[str] = []
                page.on("pageerror", lambda err: errors.append(str(err)))

                response = page.goto(url, wait_until="domcontentloaded")
                title = page.title()
                elapsed = int((time.monotonic() - start) * 1000)

                checks = [
                    {"name": "Page loaded", "expected": True, "actual": response is not None, "pass": response is not None},
                    {"name": "HTTP 2xx", "expected": "2xx", "actual": str(response.status if response else "N/A"), "pass": response is not None and 200 <= response.status < 300},
                    {"name": "Has title", "expected": "non-empty", "actual": title, "pass": bool(title)},
                    {"name": "No JS errors", "expected": 0, "actual": len(errors), "pass": len(errors) == 0},
                ]
                all_pass = all(c["pass"] for c in checks)
                return E2EResult(
                    status="pass" if all_pass else "fail",
                    url=url,
                    title=title,
                    summary=f"{url} loaded in {elapsed}ms, {len(errors)} JS errors",
                    checks=checks,
                    error=None if all_pass else "; ".join(errors),
                    duration_ms=elapsed,
                )
        except ImportError:
            return E2EResult(
                status="error",
                url=url,
                summary="Playwright not installed. Run: pip install playwright && playwright install chromium",
                error="Playwright not available",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:
            return E2EResult(
                status="error",
                url=url,
                summary=f"E2E test failed: {exc}",
                error=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
