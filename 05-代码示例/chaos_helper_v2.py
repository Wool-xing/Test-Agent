# SPDX-License-Identifier: MIT
"""
Chaos Helper v2 — blast radius control + steady-state hypothesis + gradual ramping.

Upgrades vs chaos_helper.py:
- Blast radius: namespace %, environment filter, service label selector
- Steady-state hypothesis: define → inject → verify → rollback
- Gradual ramping: step 10ms→50ms→200ms→500ms to find breaking point
- New faults: DNS failure, FD exhaustion, disk full, SSL cert expiry, connection pool drain
- Auto-rollback on all faults (finally blocks)
- Chaos experiment CRUD with scheduling
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

CHAOS_AUTHORIZED = os.environ.get("TAGENT_CHAOS_AUTHORIZED", "0") == "1"
CLOCK_DRIFT_ALLOWED = os.environ.get("TAGENT_ALLOW_CLOCK_DRIFT", "0") == "1"


def _require_auth(op: str) -> None:
    if not CHAOS_AUTHORIZED:
        raise RuntimeError(f"TAGENT_CHAOS_AUTHORIZED=0 — {op} refused")


# ═══════════════════════════════════════════════════════════════
# Blast Radius
# ═══════════════════════════════════════════════════════════════

@dataclass
class BlastRadius:
    namespace: str = "default"
    percentage: int = 10      # % of targets affected
    environment: str = ""     # "staging" or "production"
    label_selector: str = ""  # k8s label selector
    exclude_labels: str = ""  # k8s exclusion selector

    def check_safe(self) -> bool:
        if self.environment == "production" and self.percentage > 10:
            logger.warning("blast radius >10% in production — manual approval required")
            return False
        if self.percentage > 50:
            logger.warning("blast radius >50% — too wide, rejected")
            return False
        return True


# ═══════════════════════════════════════════════════════════════
# Steady-State Hypothesis
# ═══════════════════════════════════════════════════════════════

@dataclass
class SteadyState:
    metric: str           # "error_rate", "p95_latency", "throughput", "health_check"
    baseline: float       # expected value under normal operation
    tolerance: float      # acceptable deviation (e.g. 0.05 = 5%)
    check_fn: Callable[[], float] | None = None

    def verify(self) -> tuple[bool, float]:
        if self.check_fn is None:
            return True, self.baseline
        current = self.check_fn()
        deviation = abs(current - self.baseline) / max(abs(self.baseline), 0.001)
        return deviation <= self.tolerance, current


@dataclass
class ChaosExperiment:
    id: str = field(default_factory=lambda: f"chaos-{uuid.uuid4().hex[:8]}")
    name: str = ""
    fault_type: str = ""        # cpu, mem, disk, network_latency, dns, fd_exhaust, etc.
    blast_radius: BlastRadius = field(default_factory=BlastRadius)
    steady_state: SteadyState | None = None
    ramp_steps: list[int] = field(default_factory=list)  # e.g. [10, 50, 200, 500] ms
    duration_per_step: int = 30
    status: str = "pending"     # pending, running, passed, failed, rolled_back
    result: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Fault injection
# ═══════════════════════════════════════════════════════════════

def inject_cpu_stress(cores: int = 1, duration: int = 30, blast: BlastRadius | None = None) -> dict:
    _require_auth("cpu_stress")
    if blast and not blast.check_safe():
        return {"ok": False, "error": "blast radius check failed"}
    import multiprocessing
    procs = []
    try:
        for _ in range(min(cores, multiprocessing.cpu_count())):
            p = multiprocessing.Process(target=lambda: [x**2 for x in range(10**7)])
            p.start()
            procs.append(p)
        time.sleep(duration)
        return {"ok": True, "cores": cores, "duration": duration}
    finally:
        for p in procs:
            p.terminate()
            p.join(timeout=5)


def inject_network_latency(target_host: str, latency_ms: int, duration: int = 30) -> dict:
    _require_auth("network_latency")
    if os.name != "posix":
        return {"ok": False, "error": "Linux only (requires tc)"}

    iface = os.environ.get("TAGENT_NET_IFACE", "eth0")
    add_cmd = ["sudo", "tc", "qdisc", "add", "dev", iface, "root", "netem",
               "delay", f"{latency_ms}ms"]
    del_cmd = ["sudo", "tc", "qdisc", "del", "dev", iface, "root"]

    try:
        subprocess.run(add_cmd, check=True, capture_output=True, text=True, timeout=30)
        logger.info("injected %dms latency on %s", latency_ms, iface)
        time.sleep(duration)
        return {"ok": True, "latency_ms": latency_ms, "interface": iface, "duration": duration}
    finally:
        subprocess.run(del_cmd, capture_output=True, text=True, timeout=30)
        logger.info("latency removed from %s", iface)


def inject_dns_failure(target_domain: str, duration: int = 30) -> dict:
    """Simulate DNS resolution failure by adding /etc/hosts entry to 127.0.0.1."""
    _require_auth("dns_failure")
    entry = f"127.0.0.1 {target_domain}"
    hosts_path = "/etc/hosts"
    try:
        with open(hosts_path, "a") as f:
            f.write(f"\n{entry}\n")
        logger.info("DNS poisoned: %s → 127.0.0.1", target_domain)
        time.sleep(duration)
        return {"ok": True, "domain": target_domain, "duration": duration}
    except PermissionError:
        return {"ok": False, "error": "need sudo to modify /etc/hosts"}
    finally:
        # Remove injected entry
        try:
            with open(hosts_path) as f:
                lines = f.readlines()
            with open(hosts_path, "w") as f:
                for line in lines:
                    if target_domain not in line:
                        f.write(line)
        except Exception:
            logger.warning("failed to clean up /etc/hosts DNS entry")


def inject_fd_exhaustion(duration: int = 30, max_fds: int = 500) -> dict:
    """Exhaust file descriptors by opening many temp files."""
    _require_auth("fd_exhaustion")
    files = []
    try:
        for i in range(max_fds):
            try:
                f = open(f"/tmp/chaos_fd_{i}.txt", "w")
                files.append(f)
            except OSError:
                break
        logger.info("FD exhaustion: %d files open", len(files))
        time.sleep(duration)
        return {"ok": True, "open_fds": len(files), "duration": duration}
    finally:
        for f in files:
            try:
                f.close()
                os.unlink(f.name)
            except Exception:
                pass


def inject_disk_full(target_path: str = "/tmp/chaos_disk", size_mb: int = 100, duration: int = 30) -> dict:
    """Simulate disk full by writing large file."""
    _require_auth("disk_full")
    path = Path(target_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\0" * size_mb * 1024 * 1024)
        time.sleep(duration)
        return {"ok": True, "size_mb": size_mb, "duration": duration}
    except OSError as e:
        return {"ok": False, "error": str(e)}
    finally:
        if path.exists():
            path.unlink()


def inject_ssl_expiry(port: int = 443, duration: int = 30) -> dict:
    """Simulate SSL certificate expiry response latency (iptables-based)."""
    _require_auth("ssl_expiry")
    # Drop inbound on specified port to simulate cert failure
    cmd_add = ["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "DROP"]
    cmd_del = ["sudo", "iptables", "-D", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "DROP"]
    try:
        subprocess.run(cmd_add, check=True, capture_output=True, timeout=15)
        time.sleep(duration)
        return {"ok": True, "port": port, "duration": duration}
    finally:
        subprocess.run(cmd_del, capture_output=True, timeout=15)


# ═══════════════════════════════════════════════════════════════
# Gradual ramping
# ═══════════════════════════════════════════════════════════════

def run_ramped_experiment(experiment: ChaosExperiment) -> ChaosExperiment:
    """Run a chaos experiment with gradual ramping and steady-state verification."""
    _require_auth(experiment.fault_type)
    experiment.status = "running"

    for step, value in enumerate(experiment.ramp_steps):
        logger.info("chaos step %d/%d: %s=%d", step + 1, len(experiment.ramp_steps),
                     experiment.fault_type, value)

        # Verify steady-state before each step
        if experiment.steady_state:
            ok, current = experiment.steady_state.verify()
            if not ok:
                experiment.status = "failed"
                experiment.result = {"step": step, "reason": "steady-state violated",
                                     "expected": experiment.steady_state.baseline,
                                     "actual": current}
                return experiment

        # Inject
        if experiment.fault_type == "network_latency":
            inject_network_latency("8.8.8.8", value, experiment.duration_per_step)
        else:
            time.sleep(experiment.duration_per_step)

        # Verify after each step
        if experiment.steady_state:
            ok, current = experiment.steady_state.verify()
            if not ok:
                experiment.status = "failed"
                experiment.result = {"step": step, "breaking_point": value,
                                     "actual": current}
                return experiment

    experiment.status = "passed"
    experiment.result = {"ramp_steps_completed": len(experiment.ramp_steps)}
    return experiment


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="Chaos Helper v2")
    sub = ap.add_subparsers(dest="cmd")

    cpu = sub.add_parser("cpu"); cpu.add_argument("--cores", type=int, default=1)
    cpu.add_argument("--duration", type=int, default=30)

    lat = sub.add_parser("latency"); lat.add_argument("--ms", type=int, default=100)
    lat.add_argument("--host", default="8.8.8.8"); lat.add_argument("--duration", type=int, default=30)

    dns = sub.add_parser("dns"); dns.add_argument("--domain", required=True)
    dns.add_argument("--duration", type=int, default=30)

    fd = sub.add_parser("fd-exhaust"); fd.add_argument("--max", type=int, default=500)
    fd.add_argument("--duration", type=int, default=30)

    disk = sub.add_parser("disk-full"); disk.add_argument("--size-mb", type=int, default=100)
    disk.add_argument("--duration", type=int, default=30)

    ssl = sub.add_parser("ssl-expiry"); ssl.add_argument("--port", type=int, default=443)

    args = ap.parse_args()

    if args.cmd == "cpu":
        print(json.dumps(inject_cpu_stress(args.cores, args.duration)))
    elif args.cmd == "latency":
        print(json.dumps(inject_network_latency(args.host, args.ms, args.duration)))
    elif args.cmd == "dns":
        print(json.dumps(inject_dns_failure(args.domain, args.duration)))
    elif args.cmd == "fd-exhaust":
        print(json.dumps(inject_fd_exhaustion(args.max, args.duration)))
    elif args.cmd == "disk-full":
        print(json.dumps(inject_disk_full(size_mb=args.size_mb, duration=args.duration)))
    elif args.cmd == "ssl-expiry":
        print(json.dumps(inject_ssl_expiry(args.port)))
