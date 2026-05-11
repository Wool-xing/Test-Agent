"""LLM-extract delta between previous and current README + key files."""

from __future__ import annotations

import base64
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from loguru import logger

from runtime.config.settings import get_settings

SYSTEM_PROMPT = """You are an essence extractor for the Test-Agent project.

Given (a) the existing essence card in _精髓库/ and (b) the latest README + key files
from upstream, produce a SHORT delta report:

OUTPUT JSON only:
{
  "delta_summary": "≤3 sentences what changed",
  "new_skills": ["list of new skill names if any"],
  "new_rules": ["list of charter-rule-worthy ideas"],
  "new_test_methodology": ["test-related new patterns"],
  "applies_to_test_agent": true/false,
  "confidence": "high|medium|low",
  "evidence": ["quote 1", "quote 2"]
}

Be conservative: low confidence by default. Mark applies_to_test_agent=false
if the change is branding / business / unrelated.
"""


def _essence_dir() -> Path:
    s = get_settings()
    return s.project_root.parent / "_精髓库"


def _owner_repo(url: str) -> tuple[str, str]:
    parts = urlparse(url).path.strip("/").split("/")
    name = parts[1]
    if name.endswith(".git"):
        name = name[:-4]
    return parts[0], name


def fetch_current_readme(repo_url: str) -> str:
    owner, repo = _owner_repo(repo_url)
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/readme", "--jq", ".content"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return ""
        return base64.b64decode(r.stdout.strip()).decode("utf-8", "replace")[:30_000]
    except Exception as e:
        logger.warning("fetch_current_readme failed: {}", e)
        return ""


def extract_delta(essence_name: str, repo_url: str, prev_sha: str | None, new_sha: str) -> dict:
    """Call aux LLM to produce delta report."""
    existing_path = _essence_dir() / f"{essence_name}.md"
    existing = existing_path.read_text(encoding="utf-8")[:20_000] if existing_path.is_file() else ""
    current_readme = fetch_current_readme(repo_url)

    user_prompt = (
        f"### Essence name: {essence_name}\n"
        f"### Repo: {repo_url}\n"
        f"### prev_sha: {prev_sha}  new_sha: {new_sha}\n\n"
        f"## EXISTING essence card (truncated):\n```\n{existing[:8000]}\n```\n\n"
        f"## CURRENT upstream README (truncated):\n```\n{current_readme[:8000]}\n```\n\n"
        f"Produce delta JSON."
    )

    try:
        from runtime.subagent.aux_client import aux_client

        client = aux_client()
        return client.complete_json(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        logger.warning("LLM delta extraction failed: {}", e)
        return {
            "delta_summary": f"LLM unavailable, manual review required",
            "new_skills": [],
            "new_rules": [],
            "new_test_methodology": [],
            "applies_to_test_agent": False,
            "confidence": "low",
            "evidence": [],
            "error": str(e),
        }


def write_update_report(essence_name: str, repo_url: str, prev_sha: str | None, new_sha: str, delta: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    target = _essence_dir() / f"{essence_name}.update_{ts}.md"
    target.write_text(
        f"---\n"
        f"name: {essence_name} update\n"
        f"source_repo: {repo_url}\n"
        f"prev_sha: {prev_sha or 'unknown'}\n"
        f"new_sha: {new_sha}\n"
        f"detected_at: {datetime.now(timezone.utc).isoformat()}\n"
        f"confidence: llm-draft-unreviewed\n"
        f"---\n\n"
        f"# {essence_name} · Upstream Delta\n\n"
        f"## Summary\n{delta.get('delta_summary', '(none)')}\n\n"
        f"## Applies to Test-Agent?\n**{delta.get('applies_to_test_agent', False)}** (LLM confidence: {delta.get('confidence', 'low')})\n\n"
        f"## New skills\n" + "\n".join(f"- {s}" for s in delta.get("new_skills", [])) + "\n\n"
        f"## New rules\n" + "\n".join(f"- {s}" for s in delta.get("new_rules", [])) + "\n\n"
        f"## New test methodology\n" + "\n".join(f"- {s}" for s in delta.get("new_test_methodology", [])) + "\n\n"
        f"## Evidence(原文引用)\n" + "\n".join(f"> {e}" for e in delta.get("evidence", [])) + "\n\n"
        f"---\n"
        f"**Action required**: 用户审 → 改 `confidence: high/medium/low` + 填 `reviewer/last_reviewed`;若 applies_to_test_agent → 触发 Test-Agent 集成 PR;否则仅入 _精髓库 即结束。\n",
        encoding="utf-8",
    )
    return target
