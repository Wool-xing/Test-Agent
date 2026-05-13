# SPDX-License-Identifier: MIT
"""
移动端 driver 工厂 + 性能采集
被引用方：10-移动测试 agent / mobile-test skill
依赖：Appium-Python-Client, selenium
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ===== Driver Factory =====

def _build_android_caps(custom: Optional[Dict] = None) -> Dict:
    caps = {
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "deviceName": os.getenv("ANDROID_DEVICE", "emulator-5554"),
        "app": os.getenv("ANDROID_APP_PATH", ""),
        "appPackage": os.getenv("ANDROID_PACKAGE", ""),
        "appActivity": os.getenv("ANDROID_ACTIVITY", ""),
        "autoGrantPermissions": True,
        "noReset": False,
        "newCommandTimeout": 300,
    }
    if custom:
        caps.update(custom)
    return caps


def _build_ios_caps(custom: Optional[Dict] = None) -> Dict:
    caps = {
        "platformName": "iOS",
        "automationName": "XCUITest",
        "deviceName": os.getenv("IOS_DEVICE_NAME", "iPhone 15"),
        "udid": os.getenv("IOS_DEVICE_UDID", ""),
        "platformVersion": os.getenv("IOS_PLATFORM_VERSION", "17.0"),
        "app": os.getenv("IOS_APP_PATH", ""),
        "bundleId": os.getenv("IOS_BUNDLE_ID", ""),
        "autoAcceptAlerts": True,
        "newCommandTimeout": 300,
    }
    if custom:
        caps.update(custom)
    return caps


def _resolve_hub_url() -> str:
    """优先返回云真机平台 hub URL，无则用本地 Appium"""
    if os.getenv("SAUCELABS_USERNAME") and os.getenv("SAUCELABS_ACCESS_KEY"):
        u = os.environ["SAUCELABS_USERNAME"]
        k = os.environ["SAUCELABS_ACCESS_KEY"]
        return f"https://{u}:{k}@ondemand.saucelabs.com/wd/hub"
    if os.getenv("BROWSERSTACK_USERNAME") and os.getenv("BROWSERSTACK_ACCESS_KEY"):
        u = os.environ["BROWSERSTACK_USERNAME"]
        k = os.environ["BROWSERSTACK_ACCESS_KEY"]
        return f"https://{u}:{k}@hub-cloud.browserstack.com/wd/hub"
    return os.getenv("APPIUM_SERVER_URL", "http://localhost:4723")


def get_driver(platform: str, custom_caps: Optional[Dict] = None, use_cloud: bool = False):
    """
    创建 Appium driver。
    platform: 'android' | 'ios'
    use_cloud: True 强制走云真机；False 用本地 Appium（默认）
    """
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
    from appium.options.ios import XCUITestOptions

    if platform.lower() == "android":
        caps = _build_android_caps(custom_caps)
        options = UiAutomator2Options().load_capabilities(caps)
    elif platform.lower() == "ios":
        caps = _build_ios_caps(custom_caps)
        options = XCUITestOptions().load_capabilities(caps)
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    if use_cloud and not (os.getenv("SAUCELABS_USERNAME") or os.getenv("BROWSERSTACK_USERNAME")):
        raise RuntimeError(
            "use_cloud=True 但未配置云真机凭据 "
            "(需 SAUCELABS_USERNAME+SAUCELABS_ACCESS_KEY 或 "
            "BROWSERSTACK_USERNAME+BROWSERSTACK_ACCESS_KEY)"
        )
    hub_url = _resolve_hub_url()
    logger.info(f"启动 driver: {platform} → {hub_url}")
    driver = webdriver.Remote(hub_url, options=options)
    driver.implicitly_wait(10)
    return driver


# ===== 性能采集 =====

def collect_android_perf(package: str, duration: int = 60, interval: int = 1) -> list:
    """
    Android 性能采集（adb 命令）
    返回每秒一个采样点的列表，含 cpu/mem/fps。
    """
    samples = []
    end_time = time.time() + duration

    while time.time() < end_time:
        try:
            cpu_out = subprocess.run(
                ["adb", "shell", "top", "-n", "1", "-b"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            mem_out = subprocess.run(
                ["adb", "shell", "dumpsys", "meminfo", package],
                capture_output=True, text=True, timeout=5,
            ).stdout
            fps_out = subprocess.run(
                ["adb", "shell", "dumpsys", "gfxinfo", package, "framestats"],
                capture_output=True, text=True, timeout=5,
            ).stdout
        except Exception as e:
            logger.warning(f"adb 采集失败: {e}")
            continue

        cpu = _parse_top_cpu(cpu_out, package)
        mem = _parse_meminfo(mem_out)
        fps = _parse_gfxinfo_fps(fps_out)

        samples.append({
            "timestamp": datetime.now().isoformat(),
            "cpu_pct": cpu,
            "mem_mb": mem,
            "fps": fps,
        })
        time.sleep(interval)

    return samples


def _parse_top_cpu(output: str, package: str) -> Optional[float]:
    for line in output.splitlines():
        if package in line:
            parts = line.split()
            for p in parts:
                if p.endswith("%"):
                    try:
                        return float(p.rstrip("%"))
                    except ValueError:
                        pass
    return None


def _parse_meminfo(output: str) -> Optional[float]:
    for line in output.splitlines():
        if "TOTAL PSS" in line or "TOTAL:" in line:
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    return round(int(p) / 1024, 1)  # KB → MB
    return None


def _parse_gfxinfo_fps(output: str) -> Optional[float]:
    """
    粗略统计 gfxinfo framestats 帧数(非精确 FPS)。
    PROFILEDATA 段下每行 CSV 是一帧;真精确 FPS 需 timestamp 列差。
    TODO(V2.x): 解析 timestamp 列,计算 (frame_count - 1) / (timestamp[-1] - timestamp[0]) 真 FPS
    """
    frame_count = 0
    in_data = False
    for line in output.splitlines():
        stripped = line.strip()
        if "PROFILEDATA" in stripped:
            in_data = True
            continue
        if in_data:
            # CSV 行: Flags + 13 timestamps, 逗号分隔
            parts = stripped.split(",")
            if len(parts) >= 13 and parts[0].strip().lstrip("-").isdigit():
                frame_count += 1
            elif not stripped or "---" in stripped:
                in_data = False
    return float(frame_count) if frame_count > 0 else None


def collect_ios_perf(bundle_id: str, duration: int = 60) -> list:
    """iOS 性能采集（idevicediagnostics / instrumentscli）"""
    logger.warning("iOS 性能采集需 Xcode Instruments，建议用 PerfDog 或 idevicesyslog 旁路")
    return []


def save_perf_metrics(samples: list, output_dir: str, prefix: str = "perf"):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"性能数据已保存: {path}")
    return str(path)


# ===== Monkey 稳定性测试 =====

def run_monkey(
    package: str,
    event_count: int = 10000,
    throttle_ms: int = 200,
    seed: Optional[int] = None,
    serial: Optional[str] = None,
    categories: Optional[list] = None,
    pct_touch: int = 40,
    pct_motion: int = 25,
    pct_nav: int = 15,
    pct_majornav: int = 10,
    pct_syskeys: int = 5,
    pct_appswitch: int = 2,
    pct_anyevent: int = 3,
    output_dir: str = "workspace/执行日志/monkey",
    extra_args: Optional[list] = None,
    timeout: int = 3600,
) -> dict:
    """
    执行 Android Monkey 稳定性测试。

    Args:
        package: 目标 APP 包名
        event_count: 注入事件总数（默认 1 万）
        throttle_ms: 事件间隔 ms（默认 200）
        seed: 随机种子（可重放）
        serial: 设备 serial（多设备时必填）
        categories: 限制启动的 Activity category 列表
        pct_*: 各类事件百分比（合计 ≤100）
        output_dir: 日志/截图输出目录
        extra_args: 额外 monkey 参数
        timeout: 超时（秒）

    Returns:
        {"event_count", "exit_code", "log_file", "crashes", "anrs", "duration_sec"}
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(output_dir) / f"monkey_{package}_{ts}.log"

    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["shell", "monkey"]
    cmd += ["-p", package]
    cmd += ["--throttle", str(throttle_ms)]
    cmd += ["--pct-touch", str(pct_touch)]
    cmd += ["--pct-motion", str(pct_motion)]
    cmd += ["--pct-nav", str(pct_nav)]
    cmd += ["--pct-majornav", str(pct_majornav)]
    cmd += ["--pct-syskeys", str(pct_syskeys)]
    cmd += ["--pct-appswitch", str(pct_appswitch)]
    cmd += ["--pct-anyevent", str(pct_anyevent)]
    if seed is not None:
        cmd += ["-s", str(seed)]
    if categories:
        for c in categories:
            cmd += ["-c", c]
    # 默认参数：忽略崩溃/超时继续，输出 verbose
    cmd += ["--ignore-crashes", "--ignore-timeouts", "--ignore-security-exceptions",
            "--monitor-native-crashes", "--kill-process-after-error",
            "-v", "-v", "-v"]
    if extra_args:
        cmd += extra_args
    cmd += [str(event_count)]

    logger.info(f"启动 monkey: {' '.join(cmd)}")
    start = time.time()
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                                   timeout=timeout, check=False)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        logger.error(f"monkey 超时 ({timeout}s)，已强制终止")
        exit_code = -1

    duration = round(time.time() - start, 1)

    # 分析日志找 crash / ANR
    crashes = 0
    anrs = 0
    if log_file.exists():
        text = log_file.read_text(encoding="utf-8", errors="ignore")
        crashes = text.count("// CRASH")
        anrs = text.count("// NOT RESPONDING")

    result = {
        "package": package,
        "event_count": event_count,
        "throttle_ms": throttle_ms,
        "seed": seed,
        "exit_code": exit_code,
        "duration_sec": duration,
        "crashes": crashes,
        "anrs": anrs,
        "log_file": str(log_file),
        "stable": exit_code == 0 and crashes == 0 and anrs == 0,
    }

    # 同步归档 logcat（含 crash 详情）
    archive_logcat(serial=serial, output=output_dir)

    # 保存摘要 JSON
    summary = log_file.with_suffix(".json")
    summary.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"monkey 完成: 事件={event_count}, 崩溃={crashes}, ANR={anrs}, 耗时={duration}s")
    return result


# ===== logcat 归档 =====

def archive_logcat(serial: Optional[str] = None,
                   output: str = "workspace/执行日志/logcat") -> Optional[str]:
    """归档 Android logcat"""
    Path(output).mkdir(parents=True, exist_ok=True)
    file = Path(output) / f"logcat_{datetime.now():%Y%m%d_%H%M%S}.log"
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["logcat", "-d", "-v", "threadtime"]
    try:
        with open(file, "w", encoding="utf-8") as f:
            subprocess.run(cmd, stdout=f, timeout=30, check=True)
        logger.info(f"logcat 已归档: {file}")
        return str(file)
    except Exception as e:
        logger.error(f"logcat 归档失败: {e}")
        return None


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="移动端工具集")
    sub = parser.add_subparsers(dest="cmd")

    perf = sub.add_parser("collect-perf")
    perf.add_argument("--platform", choices=["android", "ios"], required=True)
    perf.add_argument("--package", required=True)
    perf.add_argument("--duration", type=int, default=60)
    perf.add_argument("--output", default="workspace/执行日志/mobile-perf")

    log = sub.add_parser("archive-logcat")
    log.add_argument("--serial", default=None)

    monkey = sub.add_parser("monkey", help="Android Monkey 稳定性测试")
    monkey.add_argument("--package", required=True)
    monkey.add_argument("--events", type=int, default=10000)
    monkey.add_argument("--throttle", type=int, default=200)
    monkey.add_argument("--seed", type=int, default=None)
    monkey.add_argument("--serial", default=None)
    monkey.add_argument("--output", default="workspace/执行日志/monkey")
    monkey.add_argument("--timeout", type=int, default=3600)

    args = parser.parse_args()
    if args.cmd == "collect-perf":
        if args.platform == "android":
            samples = collect_android_perf(args.package, args.duration)
        else:
            samples = collect_ios_perf(args.package, args.duration)
        save_perf_metrics(samples, args.output, prefix=args.package)
    elif args.cmd == "archive-logcat":
        archive_logcat(serial=args.serial)
    elif args.cmd == "monkey":
        result = run_monkey(
            package=args.package,
            event_count=args.events,
            throttle_ms=args.throttle,
            seed=args.seed,
            serial=args.serial,
            output_dir=args.output,
            timeout=args.timeout,
        )
        import sys as _sys
        _sys.exit(0 if result["stable"] else 1)


if __name__ == "__main__":
    main()
