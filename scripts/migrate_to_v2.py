#!/usr/bin/env python3
"""V1 -> V2 migration script.

Reads all Test-Agent V1 agent .md and skill .md files from ai/,
parses their YAML frontmatter and markdown body, and generates
corresponding V2 spec/manifest.yaml files under specs/.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = PROJECT_ROOT / "ai" / "agents"
SKILLS_DIR = PROJECT_ROOT / "ai" / "skills"
SPECS_DIR = PROJECT_ROOT / "specs"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

SKIP_FILES = {"README.MD", "INDEX.MD"}

# From runtime/orchestrator/adapters/experts.py
EXPERT_SCRIPT_MAP: dict[str, str | None] = {
    "test-lead": None,
    "requirements-analyst": None,
    "testcase-designer": "excel_generator.py",
    "env-manager": None,
    "data-preparer": "data_factory.py",
    "automation-engineer": None,
    "test-executor": None,
    "bug-manager": None,
    "report-generator": "generate_report.py",
    "mobile-tester": None,
    "desktop-tester": "desktop_driver.py",
    "visual-tester": None,
    "system-tester": None,
    "ai-tester": "ai_validator.py",
    "pentest-tester": None,
    "automotive-tester": None,
    "mutation-test": "mutation_runner.py",
    "chaos-test": "chaos_helper.py",
    "fuzz-test": "fuzzer.py",
    "a11y-test": "a11y_scanner.py",
    "suite-minimize": "suite_minimizer.py",
}

SKILL_SCRIPT_MAP: dict[str, str | None] = {
    "smoke-test": None,
    "regression-test": None,
    "testcase-design": "excel_generator.py",
    "python-script-gen": None,
    "jmeter-script-gen": None,
    "data-preparation": "data_factory.py",
    "zentao-bug-submission": None,
    "test-coordinator": None,
    "mobile-test": None,
    "desktop-test": "desktop_driver.py",
    "visual-test": None,
    "system-test": None,
    "ai-test": "ai_validator.py",
    "mutation-testing": "mutation_runner.py",
    "chaos-engineering": "chaos_helper.py",
    "api-fuzzing": "fuzzer.py",
    "accessibility-scan": "a11y_scanner.py",
    "test-suite-minimization": "suite_minimizer.py",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter and return (meta, body)."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, m.group(2)


def _parse_tools(tools_raw) -> list[str]:
    """Parse tools field: list or comma-separated string."""
    if isinstance(tools_raw, list):
        return [str(t).strip() for t in tools_raw if str(t).strip()]
    if isinstance(tools_raw, str):
        return [t.strip() for t in tools_raw.split(",") if t.strip()]
    return []


def _resolve_backend(impl_status: str) -> str:
    """Map V1 impl_status to V2 backend."""
    status = impl_status.strip().lower()
    if status == "script":
        return "script"
    # production, rollout, vision, unknown all default to llm
    return "llm"


def _resolve_script_path(name: str, kind: str) -> str | None:
    """Look up canonical script path from V1 script maps."""
    if kind == "agent":
        return EXPERT_SCRIPT_MAP.get(name)
    return SKILL_SCRIPT_MAP.get(name)


def _extract_description_zh(description: str, name: str) -> str:
    """Extract a short Chinese label. Falls back to name."""
    # Take the part before the first " - " or "："
    if " - " in description:
        return description.split(" - ")[0].strip()
    if "：" in description:
        return description.split("：")[0].strip()
    if ":" in description:
        return description.split(":")[0].strip()
    # First sentence
    for sep in ("。", "，", "\n"):
        if sep in description:
            return description.split(sep)[0].strip()
    return name


def _extract_requires_layer(body: str) -> list[str]:
    """Extract requires_layer hints from body if they exist."""
    # Look for explicit requires_layer: [...] in body
    m = re.search(r"requires_layer\s*:\s*\[(.+?)\]", body)
    if m:
        items = [item.strip().strip("'\"") for item in m.group(1).split(",")]
        return [i for i in items if i]
    return []


def _build_v2_manifest(
    name: str,
    kind: str,
    description: str,
    tools: list[str],
    impl_status: str,
    paired_skills: list[str] | None,
    body: str,
    requires_layer_from_meta: list[str] | None = None,
) -> dict:
    """Assemble a V2 manifest dict from parsed V1 fields."""
    # requires_layer from frontmatter takes priority; fall back to body extraction
    if requires_layer_from_meta is not None:
        requires_layer = requires_layer_from_meta
    else:
        requires_layer = _extract_requires_layer(body)

    manifest: dict = {
        "name": name,
        "version": "1.0.0",
        "kind": kind,
        "description": description,
        "description_zh": _extract_description_zh(description, name),
        "backend": _resolve_backend(impl_status),
        "tools": tools,
        "paired_skills": paired_skills or [],
        "script_path": _resolve_script_path(name, kind),
        "requires_layer": requires_layer,
        "system_prompt": body.strip(),
        "output_schema": {},
        "gates": [],
        "tags": [],
        "deprecated": False,
    }
    return manifest


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def discover_files(directory: Path, kind: str) -> list[tuple[Path, str]]:
    """Return sorted list of (path, kind) for non-skip .md files."""
    results: list[tuple[Path, str]] = []
    for md in sorted(directory.glob("*.md")):
        if md.name.upper() in SKIP_FILES:
            continue
        results.append((md, kind))
    return results


def migrate_one(file_path: Path, kind: str) -> dict | None:
    """Parse one V1 file and return a V2 manifest dict, or None on failure."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"  SKIP {file_path}: read error ({e})")
        return None

    meta, body = _parse_frontmatter(text)
    name = meta.get("name")
    if not name:
        print(f"  SKIP {file_path}: no 'name' in frontmatter")
        return None

    description = str(meta.get("description", ""))
    tools = _parse_tools(meta.get("tools", ""))

    # Determine impl_status
    status_key = "EXPERT_IMPL_STATUS" if kind == "agent" else "SKILL_IMPL_STATUS"
    impl_status = str(meta.get(status_key, "")).strip()

    # Parse paired_skills (only in agent files)
    paired_raw = meta.get("paired_skills")
    if isinstance(paired_raw, list):
        paired = [str(s).strip() for s in paired_raw if str(s).strip()]
    else:
        paired = []

    # Parse requires_layer from frontmatter (takes priority over body extraction)
    requires_layer_raw = meta.get("requires_layer")
    if isinstance(requires_layer_raw, list):
        requires_layer = [str(s).strip() for s in requires_layer_raw if str(s).strip()]
    else:
        requires_layer = None

    manifest = _build_v2_manifest(
        name=str(name),
        kind=kind,
        description=description,
        tools=tools,
        impl_status=impl_status,
        paired_skills=paired,
        requires_layer_from_meta=requires_layer,
        body=body,
    )
    return manifest


class _ManifestDumper(yaml.Dumper):
    """Custom Dumper that emits system_prompt as a literal block scalar."""


def _str_representer(dumper: yaml.Dumper, data: str) -> object:
    """Represent multiline strings with | literal block style."""
    if "\n" in data:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style="|"
        )
    if len(data) > 80:
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style=">"
        )
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str", data
    )


_ManifestDumper.add_representer(str, _str_representer)


def write_manifest(manifest: dict, dry_run: bool = False) -> Path:
    """Write manifest to specs/<kind>s/<name>/manifest.yaml. Returns target path."""
    kind = manifest["kind"]
    name = manifest["name"]
    plural = "agents" if kind == "agent" else "skills"
    target_dir = SPECS_DIR / plural / name
    target_file = target_dir / "manifest.yaml"

    if dry_run:
        return target_file

    target_dir.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.dump(
        manifest,
        Dumper=_ManifestDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    target_file.write_text(yaml_text, encoding="utf-8")
    return target_file


def run(dry_run: bool = False) -> int:
    """Main entry point. Returns exit code."""
    agents = discover_files(AGENTS_DIR, "agent")
    skills = discover_files(SKILLS_DIR, "skill")
    all_files = agents + skills

    if dry_run:
        print(f"DRY RUN — no files will be written.\n")

    print(f"Found {len(agents)} agents + {len(skills)} skills = {len(all_files)} files total.\n")

    ok_count = 0
    fail_count = 0

    for file_path, kind in all_files:
        label = "AGENT" if kind == "agent" else "SKILL"
        manifest = migrate_one(file_path, kind)
        if manifest is None:
            fail_count += 1
            continue
        target = write_manifest(manifest, dry_run=dry_run)
        status = "(dry-run)" if dry_run else "OK"
        print(f"  [{label}] {manifest['name']:30s} -> {target} {status}")
        ok_count += 1

    print(f"\nDone. {ok_count} succeeded, {fail_count} failed.")

    if ok_count != 16 + 32:
        print(f"WARNING: expected 48 files (16 agents + 32 skills), got {ok_count}")
        return 1
    return 0 if fail_count == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="V1 -> V2 migration for Test-Agent manifests")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only; do not write any files",
    )
    args = parser.parse_args()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
