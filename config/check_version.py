#!/usr/bin/env python3
"""Check if Test-Agent update is available. Called by Claude Code Stop hook.

Reads VERSION from project root, fetches remote VERSION via HTTP.
Prints notification only when newer version available.
Rate-limited: checks at most once per 24h via VERSION_last_check timestamp.
"""
import os
import time
import urllib.request
import urllib.error

VERSION_URL = "https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/VERSION"
CHECK_INTERVAL = 86400  # 24 hours


def main():
    project_root = os.getcwd()
    version_file = os.path.join(project_root, "VERSION")
    legacy_file = os.path.join(project_root, ".version")
    # Migration: rename legacy .version to VERSION if VERSION is missing
    if not os.path.isfile(version_file) and os.path.isfile(legacy_file):
        os.rename(legacy_file, version_file)

    if not os.path.isfile(version_file):
        return  # Not a Test-Agent project, skip silently

    # Rate limit: check at most once per CHECK_INTERVAL
    last_check_file = os.path.join(project_root, "VERSION_last_check")
    now = time.time()
    if os.path.isfile(last_check_file):
        try:
            with open(last_check_file, encoding="utf-8") as f:
                last = float(f.read().strip())
            if now - last < CHECK_INTERVAL:
                return
        except (ValueError, OSError):
            pass

    with open(version_file, encoding="utf-8") as f:
        local = f.read().strip()

    try:
        req = urllib.request.Request(VERSION_URL)
        req.add_header("User-Agent", "Test-Agent-version-check/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        remote = resp.read().decode().strip()
    except (urllib.error.URLError, OSError, ValueError):
        return  # Network error, skip silently

    # Write last check timestamp
    try:
        with open(last_check_file, "w", encoding="utf-8") as f:
            f.write(str(now))
    except OSError:
        pass

    if local != remote:
        print(
            f"\n📦 Test-Agent {remote} 可用（当前 {local}）。"
            f"运行 python install.py --update 更新。\n"
        )


if __name__ == "__main__":
    main()
