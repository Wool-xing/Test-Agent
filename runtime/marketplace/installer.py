"""Install / Uninstall / Archive.

安装流程:catalog 查 → verifier 跑 4 关 → 落地到 marketplace/{lane}/{name}/
卸载只归档不删
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from runtime.config.safety import SafeByDefaultBlocked, is_allowed
from runtime.config.settings import get_settings
from runtime.marketplace.catalog import Entry, find, load_local, save_local
from runtime.marketplace.verifier import run_all_gates


def _market_dir() -> Path:
    s = get_settings()
    return s.project_root / "marketplace"


def _archive_dir() -> Path:
    d = _market_dir() / ".archive"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _decisions_log(action: str, name: str, payload: dict) -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "测试报告" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = d / f"{ts}_marketplace_{action}_{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return p


def install(entry: Entry, content_path: Path) -> dict:
    """Install entry. Run 4 gates first; commit only on full pass."""
    if not is_allowed("marketplace.enabled"):
        raise SafeByDefaultBlocked(op="marketplace.install", key_path="marketplace.enabled")

    # Gates required by tier
    skip_sandbox = entry.source_tier == "high"  # high tier 信任,跳沙箱
    skip_darwin = entry.source_tier in ("high", "medium")
    min_darwin = 75 if entry.source_tier == "low" else 60

    gates = run_all_gates(content_path, expected_sha256=entry.sha256, signature=entry.signature,
                          skip_sandbox=skip_sandbox, skip_darwin=skip_darwin, min_darwin=min_darwin)
    payload = {"entry": asdict(entry), "gates": [asdict(g) for g in gates]}

    if not all(g.passed for g in gates):
        failed = [g for g in gates if not g.passed]
        _decisions_log("install_blocked", entry.name, payload)
        return {"ok": False, "name": entry.name, "blocked_by": [g.gate for g in failed], "reasons": [g.reason for g in failed]}

    # All gates passed: copy to marketplace/{lane}/{name}/
    target_dir = _market_dir() / entry.lane / entry.name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / content_path.name
    shutil.copy2(content_path, target_file)

    entry.installed_at = datetime.now(timezone.utc).isoformat()
    entries = load_local()
    # remove existing same-name entry if any (upgrade)
    entries = [e for e in entries if e.name != entry.name]
    entries.append(entry)
    save_local(entries)

    _decisions_log("install_ok", entry.name, payload | {"target": str(target_file)})
    logger.info("installed {} ({}) into {}", entry.name, entry.lane, target_dir)
    return {"ok": True, "name": entry.name, "lane": entry.lane, "path": str(target_file), "gates_passed": len(gates)}


def uninstall(name: str) -> dict:
    """Uninstall by archiving (不可逆禁止)."""
    if not is_allowed("marketplace.enabled"):
        raise SafeByDefaultBlocked(op="marketplace.uninstall", key_path="marketplace.enabled")

    entry = find(name)
    if entry is None:
        return {"ok": False, "name": name, "error": "not installed"}

    src_dir = _market_dir() / entry.lane / entry.name
    if not src_dir.is_dir():
        return {"ok": False, "name": name, "error": "files missing"}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = _archive_dir() / f"{entry.lane}_{entry.name}_{ts}"
    shutil.move(str(src_dir), str(archive))

    entries = [e for e in load_local() if e.name != name]
    save_local(entries)

    _decisions_log("uninstall", name, {"archived_to": str(archive), "entry": asdict(entry)})
    return {"ok": True, "name": name, "archived_to": str(archive)}
