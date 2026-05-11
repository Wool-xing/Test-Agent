"""Track upstream commit hash; detect changes via gh CLI."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger

from runtime.config.settings import get_settings


def _state_path() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "essence"
    d.mkdir(parents=True, exist_ok=True)
    return d / "state.json"


def _load_state() -> dict:
    p = _state_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: dict) -> None:
    _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _owner_repo(url: str) -> tuple[str, str]:
    parts = urlparse(url).path.strip("/").split("/")
    name = parts[1]
    if name.endswith(".git"):
        name = name[:-4]
    return parts[0], name


def get_head_commit(repo_url: str) -> str | None:
    """Use gh CLI to read default branch HEAD sha."""
    owner, repo = _owner_repo(repo_url)
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}", "--jq", ".default_branch"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            logger.warning("gh failed for {}/{}: {}", owner, repo, r.stderr.strip())
            return None
        default_branch = r.stdout.strip()
        r2 = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits/{default_branch}", "--jq", ".sha"],
            capture_output=True, text=True, timeout=30,
        )
        if r2.returncode != 0:
            return None
        return r2.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning("gh unavailable or timeout: {}", e)
        return None


def detect_changes(entries: list[tuple[str, str]]) -> list[dict]:
    """Return list of {essence_name, repo_url, prev_sha, new_sha}."""
    state = _load_state()
    out: list[dict] = []
    for name, url in entries:
        new_sha = get_head_commit(url)
        if new_sha is None:
            continue
        key = f"{name}::{url}"
        prev = state.get(key, {}).get("sha")
        if prev != new_sha:
            out.append({"essence_name": name, "repo_url": url, "prev_sha": prev, "new_sha": new_sha})
            state[key] = {
                "sha": new_sha,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
    _save_state(state)
    return out
