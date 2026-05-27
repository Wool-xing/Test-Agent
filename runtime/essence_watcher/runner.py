"""Essence watcher main runner.

CLI:  python -m runtime.essence_watcher.runner
Cron: 接入 runtime/scheduler 由 cron 触发(主宪章 §22)
"""

from __future__ import annotations

import json
import sys

from loguru import logger

from runtime.config.safety import SafeByDefaultBlocked, is_allowed
from runtime.essence_watcher.delta_extractor import extract_delta, write_update_report
from runtime.essence_watcher.parser import list_repos
from runtime.essence_watcher.tracker import detect_changes


def run() -> dict:
    """Main entry. Returns summary of changes detected + reports written."""
    # Safe-by-default gate (charter §24)
    if not is_allowed("essence_watcher.enabled"):
        raise SafeByDefaultBlocked(op="essence_watcher.run", key_path="essence_watcher.enabled")

    repos = list_repos()
    logger.info("essence_watcher: scanning {} repo entries", len(repos))
    changes = detect_changes(repos)
    if not changes:
        logger.info("no upstream changes detected")
        return {"checked": len(repos), "changed": 0, "reports": []}

    reports: list[str] = []
    for change in changes:
        delta = extract_delta(
            essence_name=change["essence_name"],
            repo_url=change["repo_url"],
            prev_sha=change["prev_sha"],
            new_sha=change["new_sha"],
        )
        report_path = write_update_report(
            essence_name=change["essence_name"],
            repo_url=change["repo_url"],
            prev_sha=change["prev_sha"],
            new_sha=change["new_sha"],
            delta=delta,
        )
        reports.append(str(report_path))
        logger.info("delta report written: {}", report_path)

    return {"checked": len(repos), "changed": len(changes), "reports": reports}


def main() -> int:
    try:
        summary = run()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except SafeByDefaultBlocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        logger.exception("essence_watcher failed")
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
