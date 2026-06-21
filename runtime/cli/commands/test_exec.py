"""tagent test — execute different test types (Sprint 5 CLI接入)."""

from __future__ import annotations

import typer

app = typer.Typer(name="test", help="Execute tests: e2e, visual, integration, unit")


@app.command("e2e")
def test_e2e(
    url: str = typer.Argument(..., help="URL to test"),
    browser: str = typer.Option("chromium", help="Browser: chromium, firefox, webkit"),
    headless: bool = typer.Option(True, help="Run headless"),
) -> None:
    """Run E2E browser test against a URL."""
    from runtime.testing.e2e import E2EExecutor, E2EConfig
    cfg = E2EConfig(browser=browser, headless=headless)
    executor = E2EExecutor(cfg)
    result = executor.check_page(url)
    print(f"Status: {result.status}")
    print(f"Title: {result.title}")
    print(f"Duration: {result.duration_ms}ms")
    for c in result.checks:
        icon = "[PASS]" if c["pass"] else "[FAIL]"
        print(f"  {icon} {c['name']}: {c['actual']}")
    if result.error:
        print(f"Error: {result.error}")
    if result.status != "pass":
        raise typer.Exit(code=1)


@app.command("visual")
def test_visual(
    url: str = typer.Argument(..., help="URL to capture"),
    name: str = typer.Option("baseline", help="Screenshot name"),
    compare: bool = typer.Option(False, help="Compare against baseline"),
) -> None:
    """Capture or compare screenshots for visual regression testing."""
    from runtime.testing.visual import VisualExecutor, VisualConfig
    cfg = VisualConfig()
    executor = VisualExecutor(cfg)
    if compare:
        result = executor.compare(url, name)
        print(f"Diff: {result.diff_pct}%")
    else:
        result = executor.capture(url, name)
    print(f"Status: {result.status}")
    print(f"Screenshot: {result.screenshot_path}")
    if result.error:
        print(f"Error: {result.error}")


@app.command("integration")
def test_integration(
    base_url: str = typer.Argument(..., help="Base URL for API tests"),
    path: str = typer.Option("/", help="API path to test"),
    method: str = typer.Option("GET", help="HTTP method"),
    expected_status: int = typer.Option(200, help="Expected HTTP status"),
) -> None:
    """Run API integration test."""
    from runtime.testing.integration import IntegrationExecutor, ApiCheck
    executor = IntegrationExecutor()
    checks = [ApiCheck(method=method, path=path, expected_status=expected_status)]
    result = executor.check_api(base_url, checks)
    print(f"Status: {result.status}")
    print(f"Summary: {result.summary}")
    for c in result.checks:
        icon = "[PASS]" if c["pass"] else "[FAIL]"
        print(f"  {icon} {c['name']}: {c['actual']}")
    if result.status != "pass":
        raise typer.Exit(code=1)


@app.command("unit")
def test_unit(
    path: str = typer.Argument("runtime/tests/", help="Test file or directory"),
    coverage: bool = typer.Option(False, "--cov", help="Measure coverage"),
) -> None:
    """Run unit tests with pytest."""
    from runtime.testing.unit import UnitTestExecutor, UnitTestConfig
    cfg = UnitTestConfig(coverage=coverage)
    executor = UnitTestExecutor(cfg)
    result = executor.run([path])
    print(f"Status: {result.status}")
    print(f"Results: {result.summary}")
    if result.coverage_pct > 0:
        print(f"Coverage: {result.coverage_pct}%")
    if result.status != "pass":
        raise typer.Exit(code=1)
