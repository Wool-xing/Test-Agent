"""
桌面应用 driver 工厂 + 进程性能采集
被引用方：11-桌面测试 agent / desktop-test skill
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ===== Windows =====

def get_windows_app(exe_path: Optional[str] = None, backend: str = "uia"):
    """启动 Windows 应用并返回 pywinauto Application"""
    try:
        from pywinauto import Application
    except ImportError:
        raise RuntimeError("pywinauto 未安装：pip install pywinauto")

    path = exe_path or os.getenv("WIN_APP_PATH")
    if not path:
        raise ValueError("WIN_APP_PATH 未配置")
    app = Application(backend=backend).start(path)
    logger.info(f"Windows 应用启动: {path}")
    return app


# ===== macOS =====

def open_macos_app(app_name: Optional[str] = None) -> str:
    """启动 macOS 应用（通过 open -a）"""
    name = app_name or os.getenv("MAC_APP_NAME")
    if not name:
        raise ValueError("MAC_APP_NAME 未配置")
    subprocess.run(["open", "-a", name], check=True)
    time.sleep(2)
    logger.info(f"macOS 应用启动: {name}")
    return name


def macos_menu(app_name: str, menu: str, item: str):
    """通过 AppleScript 点击 macOS 菜单"""
    script = f'''
        tell application "System Events"
            tell process "{app_name}"
                click menu item "{item}" of menu "{menu}" of menu bar 1
            end tell
        end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)


# ===== Electron =====

def launch_electron(executable_path: Optional[str] = None):
    """启动 Electron 应用，返回 (playwright, app, page)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("playwright 未安装")

    path = executable_path or os.getenv("ELECTRON_APP_PATH")
    if not path:
        raise ValueError("ELECTRON_APP_PATH 未配置")

    pw = sync_playwright().start()
    # Playwright Electron API（_impl_obj 是私有，正式用 pw.electron）
    app = pw.electron.launch(executable_path=path)
    page = app.first_window()
    logger.info(f"Electron 应用启动: {path}")
    return pw, app, page


# ===== 进程性能（跨平台 psutil）=====

def collect_proc_perf(pid: int, duration: int = 60, interval: int = 1) -> list:
    """采集进程 CPU / 内存 / IO（跨平台 psutil）"""
    try:
        import psutil
    except ImportError:
        raise RuntimeError("psutil 未安装：pip install psutil")

    proc = psutil.Process(pid)
    samples = []
    end_time = time.time() + duration

    while time.time() < end_time:
        try:
            cpu = proc.cpu_percent(interval=None)
            mem_info = proc.memory_info()
            io = proc.io_counters() if hasattr(proc, "io_counters") else None
            samples.append({
                "timestamp": datetime.now().isoformat(),
                "cpu_pct": cpu,
                "rss_mb": round(mem_info.rss / 1024 / 1024, 1),
                "vms_mb": round(mem_info.vms / 1024 / 1024, 1),
                "read_bytes": io.read_bytes if io else None,
                "write_bytes": io.write_bytes if io else None,
            })
        except psutil.NoSuchProcess:
            logger.warning("进程已退出")
            break
        time.sleep(interval)

    return samples


def save_perf(samples: list, output_dir: str, prefix: str = "desktop_perf") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


# ===== 跨平台截图 =====

def screenshot(output: str = "workspace/执行日志/desktop-screenshots/screen.png"):
    """跨平台截图"""
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    try:
        import pyautogui
        pyautogui.screenshot(output)
    except ImportError:
        # 兜底用 mss
        try:
            import mss
            with mss.mss() as sct:
                sct.shot(output=output)
        except ImportError:
            logger.error("pyautogui / mss 均未安装")
            return None
    return output


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="桌面工具集")
    sub = parser.add_subparsers(dest="cmd")

    perf = sub.add_parser("collect-perf")
    perf.add_argument("--pid", type=int, required=True)
    perf.add_argument("--duration", type=int, default=60)
    perf.add_argument("--output", default="workspace/执行日志/desktop-perf")

    shot = sub.add_parser("screenshot")
    shot.add_argument("--output", default="workspace/执行日志/desktop-screenshots/screen.png")

    args = parser.parse_args()
    if args.cmd == "collect-perf":
        samples = collect_proc_perf(args.pid, args.duration)
        save_perf(samples, args.output)
    elif args.cmd == "screenshot":
        screenshot(args.output)


if __name__ == "__main__":
    main()
