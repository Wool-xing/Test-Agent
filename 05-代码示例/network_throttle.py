"""
弱网测试工具：tc / Toxiproxy / Charles / Network Link Conditioner
被引用方：16-可靠性稳定性 agent / reliability-test skill
"""
import logging
import os
import shutil
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# 弱网预设
PRESETS = {
    "3g":         {"latency_ms": 300, "rate_kbps": 750,   "loss_pct": 1.0},
    "4g":         {"latency_ms": 80,  "rate_kbps": 4000,  "loss_pct": 0.1},
    "wifi_weak":  {"latency_ms": 200, "rate_kbps": 1000,  "loss_pct": 2.0},
    "satellite":  {"latency_ms": 600, "rate_kbps": 1000,  "loss_pct": 0.5},
    "offline":    {"latency_ms": 0,   "rate_kbps": 0,     "loss_pct": 100.0},
}


# ===== Linux tc qdisc =====

def tc_apply(interface: str = "eth0", latency_ms: int = 100,
             rate_kbps: int = 1000, loss_pct: float = 0.0):
    """Linux 用 tc + netem 设置弱网（需 root）"""
    if shutil.which("tc") is None:
        raise RuntimeError("tc 命令不可用（仅 Linux 支持，需 root）")

    # 清旧规则
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", interface, "root"],
                   capture_output=True)

    # 加 netem
    cmd = ["sudo", "tc", "qdisc", "add", "dev", interface, "root", "netem"]
    if latency_ms > 0:
        cmd += ["delay", f"{latency_ms}ms"]
    if loss_pct > 0:
        cmd += ["loss", f"{loss_pct}%"]
    if rate_kbps > 0:
        cmd += ["rate", f"{rate_kbps}kbit"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"tc 设置失败: {proc.stderr}")
    logger.info(f"tc 已应用 {interface}: latency={latency_ms}ms / rate={rate_kbps}kbps / loss={loss_pct}%")


def tc_clear(interface: str = "eth0"):
    """清除 tc 规则"""
    subprocess.run(["sudo", "tc", "qdisc", "del", "dev", interface, "root"],
                   capture_output=True)
    logger.info(f"tc 已清除 {interface}")


# ===== Android adb 弱网（针对 emulator） =====

def adb_throttle_emulator(speed: str = "edge", serial: Optional[str] = None):
    """通过 adb emu 命令限速（仅 Android emulator 支持）。
    speed: gsm | hscsd | gprs | edge | umts | hsdpa | full"""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["emu", "network", "speed", speed]
    subprocess.run(cmd, check=True)
    logger.info(f"Android emulator 限速 → {speed}")


def adb_set_loss(loss_pct: int = 5, serial: Optional[str] = None):
    """Android 模拟丢包"""
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += ["emu", "network", "loss", str(loss_pct)]
    subprocess.run(cmd, check=True)


# ===== Toxiproxy（跨平台，推荐）=====

class ToxiproxyClient:
    """Toxiproxy 客户端（HTTP API），跨平台稳定弱网"""

    def __init__(self, base_url: Optional[str] = None):
        self.base = (base_url or os.getenv("TOXIPROXY_URL", "http://localhost:8474")).rstrip("/")

    def create_proxy(self, name: str, listen: str, upstream: str) -> Dict:
        import requests
        r = requests.post(f"{self.base}/proxies", json={
            "name": name, "listen": listen, "upstream": upstream, "enabled": True,
        }, timeout=10)
        r.raise_for_status()
        return r.json()

    def add_toxic(self, proxy_name: str, toxic_type: str, attributes: Dict) -> Dict:
        """toxic_type: latency / bandwidth / slow_close / timeout / slicer / limit_data"""
        import requests
        r = requests.post(f"{self.base}/proxies/{proxy_name}/toxics", json={
            "type": toxic_type,
            "attributes": attributes,
        }, timeout=10)
        r.raise_for_status()
        return r.json()

    def remove_proxy(self, name: str):
        import requests
        requests.delete(f"{self.base}/proxies/{name}", timeout=10)


# ===== 一键应用预设 =====

def apply_preset(preset: str, mode: str = "tc", **kwargs):
    """一键应用弱网预设。mode: tc | adb | toxiproxy"""
    if preset not in PRESETS:
        raise ValueError(f"未知预设：{preset}（可选 {list(PRESETS.keys())}）")
    p = PRESETS[preset]
    if mode == "tc":
        tc_apply(latency_ms=p["latency_ms"], rate_kbps=p["rate_kbps"],
                 loss_pct=p["loss_pct"], **kwargs)
    elif mode == "adb":
        speed_map = {"3g": "edge", "4g": "hsdpa", "wifi_weak": "edge", "offline": "gsm"}
        adb_throttle_emulator(speed=speed_map.get(preset, "edge"), **kwargs)
    elif mode == "toxiproxy":
        client = ToxiproxyClient()
        # 用户需自行 create_proxy 后调 add_toxic
        return client
    else:
        raise ValueError(f"未知 mode: {mode}")


# ===== CLI =====

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="弱网工具")
    sub = parser.add_subparsers(dest="cmd")
    p1 = sub.add_parser("apply"); p1.add_argument("preset"); p1.add_argument("--mode", default="tc")
    p2 = sub.add_parser("clear"); p2.add_argument("--interface", default="eth0")
    args = parser.parse_args()
    if args.cmd == "apply":
        apply_preset(args.preset, mode=args.mode)
    elif args.cmd == "clear":
        tc_clear(args.interface)
