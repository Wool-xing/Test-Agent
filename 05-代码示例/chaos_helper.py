"""
混沌工程：故障注入（CPU/内存/磁盘/网络/进程杀死）
被引用方：16-可靠性稳定性 agent / chaos-test skill
"""
import logging
import os
import signal
import subprocess
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ===== CPU 占用 =====

def stress_cpu(cores: int = 1, duration: int = 60):
    """CPU 满载（用 stress-ng 或 fallback Python loop）"""
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
    logger.info(f"分配 {size_mb} MB 内存，持续 {duration}s")
    block = bytearray(size_mb * 1024 * 1024)
    time.sleep(duration)
    del block


# ===== 磁盘 IO 压力 =====

def stress_disk(file_path: str = "/tmp/chaos_disk_test", size_mb: int = 100, iterations: int = 10):
    """磁盘读写压力"""
    import random
    data = os.urandom(size_mb * 1024 * 1024)
    for i in range(iterations):
        with open(file_path, "wb") as f:
            f.write(data)
        with open(file_path, "rb") as f:
            f.read()
    os.remove(file_path)
    logger.info(f"磁盘压力 done: {iterations} 次 × {size_mb} MB")


# ===== 进程杀死 =====

def kill_process(pid: int, sig: int = signal.SIGKILL):
    """杀指定 PID"""
    os.kill(pid, sig)
    logger.info(f"已杀进程 PID={pid}")


def kill_by_name(name: str):
    """按名称杀进程（跨平台）"""
    try:
        import psutil
        killed = []
        for proc in psutil.process_iter(["pid", "name"]):
            if name.lower() in proc.info["name"].lower():
                proc.kill()
                killed.append(proc.info["pid"])
        return killed
    except ImportError:
        raise RuntimeError("psutil 未安装")


# ===== 容器混沌（k8s 场景）=====

def kill_pod(pod_name: str, namespace: str = "default"):
    """删 k8s pod 模拟故障（kubectl 在 PATH 中可用）"""
    cmd = ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--grace-period=0", "--force"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"kubectl delete pod 失败: {proc.stderr}")
    logger.info(f"已强制删除 pod {pod_name}")


# ===== 网络分区 =====

def block_outbound(target_host: str, duration: int = 60):
    """阻断到指定 host 的出站流量（Linux iptables，需 root）"""
    subprocess.run(["sudo", "iptables", "-A", "OUTPUT", "-d", target_host, "-j", "DROP"], check=True)
    logger.info(f"已阻断到 {target_host} 的流量，{duration}s 后恢复")
    time.sleep(duration)
    subprocess.run(["sudo", "iptables", "-D", "OUTPUT", "-d", target_host, "-j", "DROP"], check=True)
    logger.info(f"已恢复到 {target_host} 的流量")


# ===== 时钟漂移 =====

def shift_clock(seconds: int):
    """系统时钟前/后移（需 root，仅 Linux）"""
    subprocess.run(["sudo", "date", "-s", f"@{int(time.time()) + seconds}"], check=True)
    logger.info(f"时钟已 ±{seconds}s")


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="混沌工具")
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
