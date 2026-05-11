"""Parse _精髓库/INDEX.md to extract (name, repo_url) tuples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from runtime.config.settings import get_settings


@dataclass(slots=True)
class EssenceEntry:
    name: str
    file: str  # relative path within _精髓库
    repo_urls: list[str]  # may have multiple(pentest-ai-agents has 2)


REPO_URL_RE = re.compile(r"https://github\.com/([^/\s)\]]+)/([^/\s)\]]+)(?:\.git)?")
TABLE_ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|(.+)\|(.+)\|\s*$")


def _essence_dir() -> Path:
    s = get_settings()
    # _精髓库 sits sibling to project root
    return s.project_root.parent / "_精髓库"


def parse_index(index_path: Path | None = None) -> list[EssenceEntry]:
    """Parse INDEX.md table rows; return entries."""
    p = index_path or (_essence_dir() / "INDEX.md")
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8")
    entries: list[EssenceEntry] = []
    for line in text.splitlines():
        m = TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        title = m.group(1).strip()
        file_rel = m.group(2).strip()
        # extract all repo urls from the source column + title
        repos = REPO_URL_RE.findall(line)
        if not repos:
            continue
        entries.append(
            EssenceEntry(
                name=title.replace(".md", ""),
                file=file_rel,
                repo_urls=[f"https://github.com/{owner}/{name.removesuffix('.git') if name.endswith('.git') else name}" for owner, name in repos],
            )
        )
    return entries


def list_repos() -> list[tuple[str, str]]:
    """Flatten entries → (essence_name, repo_url) pairs."""
    out: list[tuple[str, str]] = []
    for e in parse_index():
        for url in e.repo_urls:
            out.append((e.name, url))
    return out
