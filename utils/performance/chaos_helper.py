# SPDX-License-Identifier: MIT
# NOTE: chaos_helper_v2.py is the enhanced version (blast radius, steady-state, ramping).
# This v1 provides simpler process-level chaos (stress_cpu/memory/disk, kill_pod).
"""
混沌工程：故障注入（CPU/内存/磁盘/网络/进程杀死）
被引用方：16-可靠性稳定性 agent / chaos-test skill

⚠️  SECURITY · 法律 / 合规 ⚠️
本模块默认 **refuse** 所有破坏性操作。授权方式：
    export TAGENT_CHAOS_AUTHORIZED=1   # 显式确认在专用混沌沙箱
    export TAGENT_ALLOW_CLOCK_DRIFT=1  # 时钟漂移单独开关(影响 TLS/Kerberos/日志)
未授权直接 raise RuntimeError，避免 CI runner 误触导致残留状态。
所有需 sudo / iptables / 改时钟的操作 **必须** 在 try/finally 中 cleanup。
"""
import logging
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


# ===== 授权 gate =====

CHAOS_AUTHORIZED = os.getenv("TAGENT_CHAOS_AUTHORIZED") == "1"
CLOCK_DRIFT_ALLOWED = os.getenv("TAGENT_ALLOW_CLOCK_DRIFT") == "1"

_HOSTNAME_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
_IPV4_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$")
_K8S_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,252}$")
_TEMP_ROOT = Path(tempfile.gettempdir()).resolve()


def _require_authorized(op: str) -> None:
    """Refuse destructive op unless TAGENT_CHAOS_AUTHORIZED=1."""
    if not CHAOS_AUTHORIZED:
        raise RuntimeError(
            f"chaos op '{op}' refused: set TAGENT_CHAOS_AUTHORIZED=1 to enable. "
            "Authorize ONLY on dedicated chaos sandboxes. "
            "Risks: CI runner state corruption, iptables残留, killed system processes, clock drift."
        )


def _validate_host(host: str) -> str:
    """Validate target_host is a plain IP or hostname (no shell metachars / args)."""
    if not isinstance(host, str) or len(host) > 253:
        raise ValueError(f"invalid host: {host!r}")
    if _IPV4_RE.match(host) or _HOSTNAME_RE.match(host):
        return host
    raise ValueError(f"refusing non-hostname/IP target: {host!r}")


def _validate_k8s_name(name: str, kind: str) -> str:
    if not isinstance(name, str) or not _K8S_NAME_RE.match(name):
        raise ValueError(f"invalid k8s {kind} name: {name!r}")
    return name


def _validate_temp_path(file_path: str) -> Path:
    """Resolve and confirm path is under system tempdir (no traversal to /etc, /var, ...)."""
    p = Path(file_path).resolve()
    try:
        p.relative_to(_TEMP_ROOT)
    except ValueError as e:
        raise ValueError(f"chaos file_path must be under {_TEMP_ROOT}, got {p}") from e
    return p


# ===== CPU 占用 =====

def stress_cpu(cores: int = 1, duration: int = 60):
    """CPU 满载（用 stress-ng 或 fallback Python loop）"""
    _require_authorized("stress_cpu")
    if cores < 1 or cores > 1024 or duration < 1 or duration > 3600:
        raise ValueError(f"invalid cores/duration: {cores}/{duration}")
    if subprocess.run(["which", "stress-ng"], capture_output=True).returncode == 0:
        subprocess.run(["stress-ng", "--cpu", str(cores), "--timeout", f"{duration}s"], check=True)
    else:
        logger.info(f"stress-ng 不可用，用 Python 模拟 CPU 满载（{cores} 线程，{duration}s）")
        end = time.time() + duration
        threads = [threading.Thread(target=_cpu_loop, args=(end,)) for _ in range(cores)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()


def _cpu_loop(end_ts):
    while time.time() < end_ts:
        pow(2, 31)


# ===== 内存占用 =====

def stress_memory(size_mb: int = 500, duration: int = 60):
    """分配指定大小内存并保持 duration 秒"""
    _require_authorized("stress_memory")
    if size_mb < 1 or size_mb > 1024 * 64 or duration < 1 or duration > 3600:
        raise ValueError(f"invalid size_mb/duration: {size_mb}/{duration}")
    logger.info(f"分配 {size_mb} MB 内存，持续 {duration}s")
    block = bytearray(size_mb * 1024 * 1024)
    time.sleep(duration)
    del block


# ===== 磁盘 IO 压力 =====

def stress_disk(file_path: Optional[str] = None, size_mb: int = 100, iterations: int = 10):
    """磁盘读写压力 · file_path 必须在系统 tempdir 内 (path traversal guard)"""
    _require_authorized("stress_disk")
    if size_mb < 1 or size_mb > 1024 * 16 or iterations < 1 or iterations > 1000:
        raise ValueError(f"invalid size_mb/iterations: {size_mb}/{iterations}")

    if file_path is None:
        fd, file_path_real = tempfile.mkstemp(prefix="chaos_disk_", suffix=".bin")
        os.close(fd)
        target = Path(file_path_real)
    else:
        target = _validate_temp_path(file_path)

    try:
        data = os.urandom(size_mb * 1024 * 1024)
        for i in range(iterations):
            with open(target, "wb") as f:
                f.write(data)
            with open(target, "rb") as f:
                f.read()
        logger.info(f"磁盘压力 done: {iterations} 次 × {size_mb} MB · {target}")
    finally:
        try:
            target.unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"chaos_disk cleanup failed: {target} · {e}")


# ===== 进程杀死 =====

_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)  # Windows compat

def kill_process(pid: int, sig: int = _SIGKILL):
    """杀指定 PID · 拒绝 PID<100 / 非当前 user owner 的进程"""
    _require_authorized("kill_process")
    if not isinstance(pid, int) or pid < 100:
        raise ValueError(f"refusing to kill system PID {pid} (must be ≥100)")
    psutil_ok = False
    try:
        import psutil
        proc = psutil.Process(pid)
        if proc.username() != psutil.Process(os.getpid()).username():
            raise PermissionError(
                f"refusing to kill PID {pid}: owner {proc.username()} ≠ self {psutil.Process(os.getpid()).username()}"
            )
        psutil_ok = True
    except ImportError:
        raise RuntimeError("psutil not installed — required for owner validation; pip install psutil")
    if not psutil_ok:
        raise RuntimeError("psutil owner check failed — refusing to kill")
    os.kill(pid, sig)
    logger.info(f"已杀进程 PID={pid}")


def kill_by_name(name: str):
    """按名称杀进程(跨平台)· 仅杀当前 user 拥有的进程"""
    _require_authorized("kill_by_name")
    if not isinstance(name, str) or not name.strip() or len(name) > 64:
        raise ValueError(f"invalid process name: {name!r}")
    try:
        import psutil
    except ImportError as e:
        raise RuntimeError("psutil 未安装") from e
    self_user = psutil.Process(os.getpid()).username()
    killed = []
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            if (
                name.lower() in (proc.info.get("name") or "").lower()
                and proc.info.get("username") == self_user
                and proc.info["pid"] >= 100
            ):
                proc.kill()
                killed.append(proc.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed


# ===== 容器混沌(k8s 场景)=====

def kill_pod(pod_name: str, namespace: str = "default"):
    """删 k8s pod 模拟故障 · pod_name / namespace 必须合规 k8s name"""
    _require_authorized("kill_pod")
    pod_name = _validate_k8s_name(pod_name, "pod")
    namespace = _validate_k8s_name(namespace, "namespace")
    cmd = ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--grace-period=0", "--force"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"kubectl delete pod 失败: {proc.stderr}")
    logger.info(f"已强制删除 pod {pod_name}")


# ===== 网络分区 =====

def block_outbound(target_host: str, duration: int = 60):
    """阻断到指定 host 的出站流量(Linux iptables,需 root)· try/finally 保 cleanup"""
    _require_authorized("block_outbound")
    target_host = _validate_host(target_host)
    if duration < 1 or duration > 3600:
        raise ValueError(f"invalid duration: {duration}")

    add_cmd = ["sudo", "-n", "iptables", "-A", "OUTPUT", "-d", target_host, "-j", "DROP"]
    del_cmd = ["sudo", "-n", "iptables", "-D", "OUTPUT", "-d", target_host, "-j", "DROP"]

    add_proc = subprocess.run(add_cmd, capture_output=True, text=True, timeout=30)
    if add_proc.returncode != 0:
        raise RuntimeError(f"iptables add 失败 (sudo 需免密 or root): {add_proc.stderr}")
    logger.info(f"已阻断到 {target_host} 的流量,{duration}s 后恢复")

    try:
        time.sleep(duration)
    finally:
        del_proc = subprocess.run(del_cmd, capture_output=True, text=True, timeout=30)
        if del_proc.returncode != 0:
            logger.error(
                f"⚠ iptables cleanup 失败 · runner 残留 DROP rule! "
                f"手动清: sudo iptables -D OUTPUT -d {target_host} -j DROP · stderr={del_proc.stderr}"
            )
        else:
            logger.info(f"已恢复到 {target_host} 的流量")


# ===== 时钟漂移 =====

def shift_clock(seconds: int, auto_restore: bool = True):
    """系统时钟前/后移(需 root,仅 Linux)· 双 env var gate· auto_restore=默认自动回滚"""
    _require_authorized("shift_clock")
    if not CLOCK_DRIFT_ALLOWED:
        raise RuntimeError(
            "shift_clock refused: set TAGENT_ALLOW_CLOCK_DRIFT=1 (separate from CHAOS_AUTHORIZED). "
            "Clock drift breaks TLS cert validation, Kerberos auth, log ordering."
        )
    if not isinstance(seconds, int) or abs(seconds) > 86400:
        raise ValueError(f"invalid seconds: {seconds} (max ±86400)")
    original_time = int(time.time())
    try:
        subprocess.run(["sudo", "-n", "date", "-s", f"@{original_time + seconds}"], check=True, timeout=30)
        logger.info(f"时钟已 ±{seconds}s (auto_restore={auto_restore})")
    finally:
        if auto_restore:
            subprocess.run(["sudo", "-n", "date", "-s", f"@{original_time}"], check=False, timeout=30)
            logger.info("时钟已自动恢复到原时间")


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="混沌工具 · 默认 refuse, 设 TAGENT_CHAOS_AUTHORIZED=1 启用")
    sub = parser.add_subparsers(dest="cmd")
    cpu = sub.add_parser("cpu"); cpu.add_argument("--cores", type=int, default=1); cpu.add_argument("--duration", type=int, default=60)
    mem = sub.add_parser("mem"); mem.add_argument("--size", type=int, default=500); mem.add_argument("--duration", type=int, default=60)
    disk = sub.add_parser("disk"); disk.add_argument("--size", type=int, default=100); disk.add_argument("--iter", type=int, default=10)
    kp = sub.add_parser("kill-pod"); kp.add_argument("name"); kp.add_argument("--ns", default="default")
    bo = sub.add_parser("block"); bo.add_argument("host"); bo.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()
    if args.cmd == "cpu":
        stress_cpu(args.cores, args.duration)
    elif args.cmd == "mem":
        stress_memory(args.size, args.duration)
    elif args.cmd == "disk":
        stress_disk(size_mb=args.size, iterations=args.iter)
    elif args.cmd == "kill-pod":
        kill_pod(args.name, args.ns)
    elif args.cmd == "block":
        block_outbound(args.host, args.duration)
