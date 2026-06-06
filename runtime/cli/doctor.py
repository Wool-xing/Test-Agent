"""Doctor — comprehensive environment health check.

Verifies: LLM, catalog, config, deps, MCP, workspace, network.
"""

from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

Checks = list[dict[str, Any]]


def _ok(label: str, detail: str = "") -> dict[str, Any]:
    return {"label": label, "ok": True, "detail": detail}


def _warn(label: str, detail: str) -> dict[str, Any]:
    return {"label": label, "ok": True, "detail": f"[yellow]⚠ {detail}[/]"}


def _fail(label: str, detail: str) -> dict[str, Any]:
    return {"label": label, "ok": False, "detail": f"[red]✗ {detail}[/]"}


def check_catalog() -> Checks:
    """Verify agent/skill catalog loads correctly."""
    try:
        from runtime.registry.registry import build_catalog
        cat = build_catalog()
        return [
            _ok("Catalog load", f"{len(cat.experts)} experts, {len(cat.skills)} skills"),
        ]
    except Exception as e:
        return [_fail("Catalog load", str(e))]


def check_config() -> Checks:
    """Check .env and VERSION files."""
    results: Checks = []
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        results.append(_ok(".env file", "found"))
    else:
        example = Path.cwd() / "config" / ".env.example"
        results.append(_warn(".env file", f"not found; copy from {example}"))
    version_file = Path.cwd() / "VERSION"
    if version_file.is_file():
        ver = version_file.read_text().strip()
        results.append(_ok("VERSION file", ver))
    else:
        results.append(_fail("VERSION file", "missing"))
    return results


def check_dependencies() -> Checks:
    """Check critical import dependencies."""
    results: Checks = []
    critical = {
        "pydantic": "Schema validation",
        "httpx": "HTTP client",
        "defusedxml": "Safe XML parsing",
        "yaml": "Config loading",
        "fastapi": "API server",
    }
    for module, purpose in critical.items():
        try:
            importlib.import_module(module)
            results.append(_ok(purpose, module))
        except ImportError:
            results.append(_fail(purpose, f"{module} not installed"))
    return results


def check_llm() -> Checks:
    """Verify LLM provider connectivity."""
    provider = os.environ.get("TAGENT_LLM_PROVIDER", "stub")
    if provider == "stub":
        return [_warn("LLM provider", "stub mode (no external calls)")]

    api_key = os.environ.get("TAGENT_LLM_API_KEY", "")
    has_key = bool(api_key)
    results = [_ok("LLM API key", "configured") if has_key else _warn("LLM API key", "not set")]

    # Quick connectivity check
    try:
        import httpx
        endpoints = {
            "openai": "https://api.openai.com/v1/models",
            "claude": "https://api.anthropic.com/v1/messages",
            "deepseek": "https://api.deepseek.com/v1/models",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
        }
        url = endpoints.get(provider)
        if url:
            t0 = time.time()
            r = httpx.get(url, timeout=5)
            elapsed = (time.time() - t0) * 1000
            if r.status_code < 500:
                results.append(_ok(f"{provider} endpoint", f"{int(elapsed)}ms"))
            else:
                results.append(_warn(f"{provider} endpoint", f"HTTP {r.status_code}"))
    except Exception:
        results.append(_warn(f"{provider} endpoint", "unreachable (network may be fine)"))
    return results


def check_workspace() -> Checks:
    """Verify workspace directory is writable."""
    ws = Path.cwd() / "workspace"
    results: Checks = []
    if ws.is_dir():
        results.append(_ok("workspace/", "exists"))
    else:
        try:
            ws.mkdir(parents=True, exist_ok=True)
            results.append(_ok("workspace/", "created"))
        except OSError as e:
            return [_fail("workspace/", str(e))]
    test_file = ws / ".doctor_write_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
        results.append(_ok("workspace writable", "ok"))
    except OSError:
        results.append(_fail("workspace writable", "permission denied"))
    return results


def check_mcp() -> Checks:
    """Check MCP server availability."""
    try:
        import mcp  # noqa: F401
        return [_ok("MCP SDK", "installed")]
    except ImportError:
        return [_warn("MCP SDK", "not installed (optional)")]


def check_environment() -> Checks:
    """Run platform-specific environment checks."""
    results: Checks = []
    results.append(_ok("Platform", sys.platform))
    results.append(_ok("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"))
    try:
        import runtime
        results.append(_ok("Runtime", runtime.__version__))
    except Exception:
        results.append(_warn("Runtime", "version unknown"))
    return results


def run_doctor() -> tuple[Checks, int, int]:
    """Run all health checks. Returns (results, ok_count, warn_count)."""
    all_checks: Checks = []
    for name, fn in [
        ("Environment", check_environment),
        ("Catalog", check_catalog),
        ("Config", check_config),
        ("Dependencies", check_dependencies),
        ("LLM", check_llm),
        ("Workspace", check_workspace),
        ("MCP", check_mcp),
    ]:
        all_checks.append({"section": name, "checks": fn()})
        logger.info("doctor: {} checked", name)

    ok = sum(1 for c in all_checks for ch in c["checks"] if ch["ok"])
    warn = sum(1 for c in all_checks for ch in c["checks"] if ch["ok"] and "warn" in str(ch.get("detail", "")))
    return all_checks, ok, warn
