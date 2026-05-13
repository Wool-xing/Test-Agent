# SPDX-License-Identifier: MIT
"""
桌面应用 driver 工厂 + 进程性能采集
被引用方：11-桌面测试 agent / desktop-test skill

安全约束（W5-5 加固）：
    macOS 自动化函数 (open_macos_app / macos_menu) 通过 subprocess 调用
    `open` / `osascript`, 其中 AppleScript 由 f-string 拼接, 历史上存在
    AppleScript 注入面 (用户控 app_name / menu / item)。准入控制：
      - 需环境变量 TAGENT_DESKTOP_AUTHORIZED=1 显式授权。
      - 平台必须为 darwin (非 macOS 自动 refuse)。
      - 所有 AppleScript identifier (app name / menu / item) 经正则白名单校验。
    授权 ONLY 在自有 macOS 测试机。生产 macOS 设备严禁。
"""
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ===== W5-5 安全 gate =====

GATE_ENV_VAR = "TAGENT_DESKTOP_AUTHORIZED"
# AppleScript identifier: 首字符字母, 允许字母 / 数字 / 空格 / 下划线 / 点 / 短横, 最长 128 字符
_AS_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 _.\-]{0,127}$")


def _gate_enabled() -> bool:
    return os.getenv(GATE_ENV_VAR) == "1"


def _require_authorized(op: str) -> None:
    """桌面自动化操作准入守卫。"""
    if not _gate_enabled():
        raise RuntimeError(
            f"desktop op '{op}' refused: set {GATE_ENV_VAR}=1 to enable. "
            "Authorize ONLY on macOS test machines you own. "
            "Risks: subprocess invocation, AppleScript execution, "
            "arbitrary app launch."
        )


def _require_macos(op: str) -> None:
    """macOS only 守卫 (非 darwin 平台拒绝)。"""
    if sys.platform != "darwin":
        raise RuntimeError(
            f"desktop op '{op}' is macOS-only (current platform: {sys.platform!r}). "
            "Use get_windows_app / launch_electron / collect_proc_perf for cross-platform."
        )


def _validate_as_identifier(name: str, kind: str = "identifier") -> str:
    """AppleScript identifier 白名单校验, 防 AppleScript / shell 注入。"""
    if not isinstance(name, str) or not _AS_IDENT_RE.fullmatch(name):
        raise ValueError(
            f"invalid AppleScript {kind}: {name!r}. allowed pattern: "
            r"^[A-Za-z][A-Za-z0-9 _.\-]{0,127}$ "
            "(starts with letter; letters/digits/space/underscore/dot/hyphen only)"
        )
    return name


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
    """启动 macOS 应用 (通过 open -a)。

    安全：需 TAGENT_DESKTOP_AUTHORIZED=1 + platform=darwin + app_name 白名单。
    """
    _require_authorized("open_macos_app")
    _require_macos("open_macos_app")
    name = app_name or os.getenv("MAC_APP_NAME")
    if not name:
        raise ValueError("MAC_APP_NAME 未配置")
    _validate_as_identifier(name, "app name")
    subprocess.run(["open", "-a", name], check=True)
    time.sleep(2)
    logger.info(f"macOS 应用启动: {name}")
    return name


def macos_menu(app_name: str, menu: str, item: str):
    """通过 AppleScript 点击 macOS 菜单。

    安全：
      - 需 TAGENT_DESKTOP_AUTHORIZED=1 + platform=darwin。
      - app_name / menu / item 三者均经 AppleScript identifier 白名单校验,
        防 AppleScript 注入 (历史上 f-string 拼接可逃逸引号执行 do shell script)。
    """
    _require_authorized("macos_menu")
    _require_macos("macos_menu")
    _validate_as_identifier(app_name, "app name")
    _validate_as_identifier(menu, "menu name")
    _validate_as_identifier(item, "menu item")
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
