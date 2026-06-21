"""Visual regression testing — screenshot capture and comparison (Sprint 5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VisualConfig:
    threshold: float = 0.05  # 5% pixel difference threshold
    viewport_width: int = 1280
    viewport_height: int = 720
    output_dir: str = "workspace/visual-tests"


@dataclass
class VisualResult:
    status: str  # pass | fail | error
    url: str
    diff_pct: float = 0.0
    screenshot_path: str = ""
    baseline_path: str = ""
    summary: str = ""
    error: str | None = None
    duration_ms: int = 0


class VisualExecutor:
    """Capture screenshots and compare against baselines for visual regression."""

    def __init__(self, config: VisualConfig | None = None):
        self._config = config or VisualConfig()

    @staticmethod
    def _safe_name(name: str) -> str:
        if not name or not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid name: {name!r} — use only alphanumeric, hyphens, underscores")
        if ".." in name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid name: {name!r} — path separators not allowed")
        return name

    def capture(self, url: str, name: str) -> VisualResult:
        """Capture a screenshot of a URL and save as a baseline or comparison."""
        import time

        name = self._safe_name(name)
        start = time.monotonic()
        out_dir = Path(self._config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = out_dir / f"{name}.png"

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": self._config.viewport_width, "height": self._config.viewport_height}
                )
                page.goto(url, wait_until="networkidle")
                page.screenshot(path=str(screenshot_path), full_page=False)
                browser.close()

            return VisualResult(
                status="pass",
                url=url,
                screenshot_path=str(screenshot_path),
                summary=f"Screenshot captured: {screenshot_path}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except ImportError:
            return VisualResult(status="error", url=url, error="Playwright not installed", duration_ms=0)
        except Exception as exc:
            return VisualResult(status="error", url=url, error=str(exc), duration_ms=0)

    def compare(self, url: str, baseline_name: str) -> VisualResult:
        """Compare current screenshot against a stored baseline."""
        import time

        baseline_name = self._safe_name(baseline_name)
        start = time.monotonic()
        out_dir = Path(self._config.output_dir)
        baseline_path = out_dir / f"{baseline_name}.png"
        current_path = out_dir / f"{baseline_name}_current.png"

        if not baseline_path.exists():
            return VisualResult(
                status="error",
                url=url,
                baseline_path=str(baseline_path),
                error=f"Baseline not found: {baseline_path}. Run capture first.",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # Capture current
        result = self.capture(url, f"{baseline_name}_current")
        if result.status != "pass":
            return result

        # Simple pixel comparison via PIL
        try:
            from PIL import Image
            import numpy as np

            baseline = np.array(Image.open(baseline_path))
            current = np.array(Image.open(current_path))

            if baseline.shape != current.shape:
                return VisualResult(
                    status="fail",
                    url=url,
                    diff_pct=100.0,
                    screenshot_path=str(current_path),
                    baseline_path=str(baseline_path),
                    summary=f"Dimension mismatch: {baseline.shape} vs {current.shape}",
                    duration_ms=int((time.monotonic() - start) * 1000),
                )

            diff = np.abs(baseline.astype(float) - current.astype(float))
            diff_pct = float(np.mean(diff > 10) * 100)  # pixels differing by >10
            passed = diff_pct <= self._config.threshold * 100

            return VisualResult(
                status="pass" if passed else "fail",
                url=url,
                diff_pct=round(diff_pct, 2),
                screenshot_path=str(current_path),
                baseline_path=str(baseline_path),
                summary=f"Visual diff: {diff_pct:.1f}% (threshold {self._config.threshold*100:.0f}%)",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except ImportError:
            return VisualResult(status="error", url=url, error="PIL/numpy not installed for visual comparison")
        except Exception as exc:
            return VisualResult(status="error", url=url, error=str(exc))
