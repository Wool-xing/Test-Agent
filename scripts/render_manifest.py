#!/usr/bin/env python3
"""Manifest V2 -> Markdown renderer.

Reads manifest.yaml from specs/agents/<name>/ or specs/skills/<name>/
and generates the corresponding .md file for AI Mode.

This is the REVERSE of migrate_to_v2.py -- takes the manifest.yaml
single source of truth and renders it into the V1-compatible .md format
with YAML frontmatter + markdown body.

Usage:
    python scripts/render_manifest.py              # render all 48
    python scripts/render_manifest.py --name test-lead   # render one
    python scripts/render_manifest.py --dry-run    # preview only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = PROJECT_ROOT / "specs"
AI_AGENTS_DIR = PROJECT_ROOT / "ai" / "agents"
AI_SKILLS_DIR = PROJECT_ROOT / "ai" / "skills"

# Reverse mapping from V2 backend to V1 IMPL_STATUS
BACKEND_TO_STATUS: dict[str, str] = {
    "llm": "production",
    "script": "script",
    "noop": "rollout",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_frontmatter(manifest: dict) -> str:
    """Build V1-compatible YAML frontmatter from a manifest dict.

    Format matches the existing V1 .md files exactly:
    plain scalars (no unnecessary quoting), comma-separated tools,
    inline list for paired_skills.
    """
    kind = manifest["kind"]
    name = manifest["name"]
    description = manifest.get("description", "")
    tools = manifest.get("tools", [])
    backend = manifest.get("backend", "llm")
    paired_skills = manifest.get("paired_skills", [])
    requires_layer = manifest.get("requires_layer", [])

    # Determine V1 status key and value
    if kind == "agent":
        status_key = "EXPERT_IMPL_STATUS"
    else:
        status_key = "SKILL_IMPL_STATUS"
    status_value = BACKEND_TO_STATUS.get(backend, "production")

    # Build frontmatter lines (V1 uses plain scalars, no quoting)
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(f"description: {description}")
    lines.append(f"tools: {', '.join(tools)}")

    # requires_layer (only emit when non-empty)
    if requires_layer:
        rl_str = "[" + ", ".join(requires_layer) + "]"
        lines.append(f"requires_layer: {rl_str}")

    lines.append(f"{status_key}: {status_value}")

    # Paired skills (agents only -- always emit, even empty, to match V1)
    if kind == "agent":
        ps_str = "[" + ", ".join(paired_skills) + "]"
        lines.append(f"paired_skills: {ps_str}")

    lines.append("---")
    return "\n".join(lines)


def _load_manifest(kind: str, name: str) -> dict:
    """Load a manifest.yaml from specs/<kind>s/<name>/manifest.yaml."""
    plural = "agents" if kind == "agent" else "skills"
    path = SPECS_DIR / plural / name / "manifest.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _render_md(manifest: dict) -> str:
    """Render a full V1 .md file from a manifest dict."""
    frontmatter = _build_frontmatter(manifest)
    system_prompt = manifest.get("system_prompt", "")
    return frontmatter + "\n\n" + system_prompt + "\n"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _discover_all() -> list[tuple[str, str]]:
    """Return sorted list of (kind, name) for all manifests under specs/."""
    results: list[tuple[str, str]] = []

    for kind, plural in [("agent", "agents"), ("skill", "skills")]:
        dir_path = SPECS_DIR / plural
        if not dir_path.is_dir():
            continue
        for subdir in sorted(dir_path.iterdir()):
            if not subdir.is_dir():
                continue
            manifest_file = subdir / "manifest.yaml"
            if manifest_file.is_file():
                results.append((kind, subdir.name))

    return results


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _render_one(kind: str, name: str, dry_run: bool = False) -> Path:
    """Render one manifest to .md. Returns the target file path."""
    manifest = _load_manifest(kind, name)
    md_text = _render_md(manifest)

    target_dir = AI_AGENTS_DIR if kind == "agent" else AI_SKILLS_DIR
    target_file = target_dir / f"{name}.md"

    if not dry_run:
        # Normalize to LF line endings to match V1 originals
        md_text = md_text.replace("\r\n", "\n")
        with open(target_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(md_text)

    return target_file


def _run(dry_run: bool = False, names: list[str] | None = None) -> int:
    """Main entry point. Returns exit code."""
    manifests = _discover_all()

    if names:
        # Filter to requested names
        manifests = [
            (k, n) for k, n in manifests if n in names
        ]
        if not manifests:
            print(f"No manifests found matching: {names}")
            return 1

    if dry_run:
        print("DRY RUN -- no files will be written.\n")

    print(f"Found {len(manifests)} manifest(s) to render.\n")

    ok = 0
    fail = 0

    for kind, name in manifests:
        label = "AGENT" if kind == "agent" else "SKILL"
        try:
            target = _render_one(kind, name, dry_run=dry_run)
            status = "(dry-run)" if dry_run else "OK"
            print(f"  [{label}] {name:30s} -> {target} {status}")
            ok += 1
        except Exception as e:
            print(f"  [{label}] {name:30s} FAIL: {e}")
            fail += 1

    print(f"\nDone. {ok} succeeded, {fail} failed.")

    return 0 if fail == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render V2 manifest.yaml -> V1 .md files"
    )
    parser.add_argument(
        "--name",
        help="Render a single manifest by name (e.g. 'test-lead', 'smoke-test')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only; do not write any files",
    )
    args = parser.parse_args()
    names = [args.name] if args.name else None
    sys.exit(_run(dry_run=args.dry_run, names=names))


if __name__ == "__main__":
    main()
