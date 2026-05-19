# SPDX-License-Identifier: MIT
"""CI Contract Gate — L7 Shift-Left contract test pipeline.

Detects OpenAPI spec changes in PR, generates consumer contracts,
and validates against provider. Blocks PR if contract broken.

Usage:
  python ci_contract_gate.py --base-ref origin/main --spec-dir specs/ --provider-url http://localhost:8800
  python ci_contract_gate.py --changed-specs openapi.json --consumer test-agent --provider-url http://api:8800
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SPEC_PATTERNS = [
    "openapi.json", "openapi.yaml", "openapi.yml",
    "swagger.json", "swagger.yaml", "swagger.yml",
    "**/openapi.json", "**/openapi.yaml", "**/openapi.yml",
    "**/swagger.json", "**/swagger.yaml", "**/swagger.yml",
    "specs/**/*.json", "specs/**/*.yaml", "specs/**/*.yml",
    "api/**/*.json", "api/**/*.yaml", "api/**/*.yml",
]


def find_changed_specs(base_ref: str = "origin/main", spec_dir: str = "") -> list[str]:
    """Find changed OpenAPI spec files via git diff."""
    cmd = ["git", "diff", "--name-only", base_ref, "HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("git diff failed: %s", result.stderr)
        return []

    changed = set(result.stdout.strip().split("\n"))
    specs: list[str] = []
    for pattern in SPEC_PATTERNS:
        import fnmatch
        import glob as globmod

        if spec_dir:
            for f in globmod.glob(f"{spec_dir}/**/*.{'json','yaml','yml'}", recursive=True):
                if f in changed:
                    specs.append(f)
        else:
            for f in changed:
                if fnmatch.fnmatch(f, pattern):
                    specs.append(f)
    # dedup
    return sorted(set(specs))


def generate_contract(spec_file: str, consumer: str, output_dir: str = "workspace/contracts") -> str | None:
    """Generate Pact contract from OpenAPI spec."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output = Path(output_dir) / f"{Path(spec_file).stem}-contract.json"

    cmd = [
        sys.executable, "-m", "contract_test_generator",
        "from-openapi",
        "--schema", spec_file,
        "--consumer", consumer,
        "--output", str(output),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Contract generation failed for %s: %s", spec_file, result.stderr)
        return None
    logger.info("Contract generated: %s", output)
    return str(output)


def verify_contract(contract_file: str, provider_url: str) -> dict[str, Any]:
    """Verify generated contract against provider."""
    cmd = [
        sys.executable, "-m", "contract_test",
        "verify",
        contract_file,
        provider_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"valid": False, "error": result.stderr, "details": []}

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "error": f"Invalid JSON: {result.stdout[:200]}", "details": []}

    return data


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="CI Contract Gate (L7 Shift-Left)")
    parser.add_argument("--base-ref", default="origin/main", help="Base reference for git diff")
    parser.add_argument("--changed-specs", nargs="*", help="Explicit list of changed spec files")
    parser.add_argument("--spec-dir", default="", help="Directory to scan for specs")
    parser.add_argument("--consumer", default="test-agent", help="Consumer name for contract")
    parser.add_argument("--provider-url", default="", help="Provider base URL for verification")
    parser.add_argument("--output-dir", default="workspace/contracts", help="Contract output directory")
    parser.add_argument("--output-json", default="", help="Write gate result JSON")
    args = parser.parse_args()

    # 1. Find changed specs
    if args.changed_specs:
        specs = list(args.changed_specs)
    else:
        specs = find_changed_specs(args.base_ref, args.spec_dir)

    if not specs:
        logger.info("No OpenAPI spec changes detected — contract gate skipped (pass)")
        gate_result = {"pass": True, "message": "No spec changes", "contracts": []}
        if args.output_json:
            Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output_json).write_text(json.dumps(gate_result, indent=2))
        print("✅ Contract gate: no spec changes")
        sys.exit(0)

    logger.info("Detected %d changed spec(s): %s", len(specs), ", ".join(specs))

    # 2. Generate & verify contracts
    all_pass = True
    results: list[dict[str, Any]] = []

    for spec_file in specs:
        if not Path(spec_file).exists():
            logger.warning("Spec file not found: %s", spec_file)
            continue

        contract_file = generate_contract(spec_file, args.consumer, args.output_dir)
        if not contract_file:
            all_pass = False
            results.append({"spec": spec_file, "pass": False, "error": "Contract generation failed"})
            continue

        if args.provider_url:
            verification = verify_contract(contract_file, args.provider_url)
            passed = verification.get("matched", 0) == verification.get("total", 1) and verification.get("total", 0) > 0
            results.append({
                "spec": spec_file,
                "contract": contract_file,
                "pass": passed,
                "total": verification.get("total", 0),
                "matched": verification.get("matched", 0),
                "details": verification.get("details", []),
            })
            if not passed:
                all_pass = False
                logger.error("Contract verification failed for %s", spec_file)
            else:
                logger.info("Contract verified: %s (%s/%s)", spec_file,
                           verification.get("matched", 0), verification.get("total", 0))
        else:
            results.append({"spec": spec_file, "contract": contract_file, "pass": True, "note": "No provider URL for verification"})
            logger.info("Contract generated: %s (no provider verification)", spec_file)

    # 3. Output
    gate_result = {
        "pass": all_pass,
        "message": "All contracts verified" if all_pass else "Contract verification failed",
        "contracts": results,
    }

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(gate_result, indent=2, ensure_ascii=False), encoding="utf-8")

    if all_pass:
        print("✅ Contract gate: all contracts pass")
    else:
        print("❌ Contract gate: contract verification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
