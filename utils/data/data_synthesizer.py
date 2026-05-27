# SPDX-License-Identifier: MIT
"""
Test data synthesis — production shadow copy + PII automatic masking.

Use: creates realistic test data without exposing real PII.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── PII detection patterns ───────────────────────────────────

_PII_PATTERNS: Dict[str, re.Pattern] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone_cn": re.compile(r"1[3-9]\d{9}"),
    "id_card": re.compile(r"\d{17}[\dXx]"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
}

_MASK_TEMPLATES = {
    "email": "user_{hash}@example.com",
    "phone_cn": "138{hash:08d}",
    "id_card": "{hash:17d}",
    "ipv4": "10.{a}.{b}.{c}",
    "credit_card": "4111-{hash:04d}-{hash:04d}-{hash:04d}",
}


def _hash_value(value: str, length: int = 6) -> str:
    d = hashlib.sha256(value.encode()).hexdigest()[:length]
    return str(int(d, 16) % (10 ** min(length, 8)))


def mask_pii(text: str) -> tuple[str, int]:
    """Replace detected PII with deterministic masks. Returns (masked_text, count)."""
    count = 0
    result = text
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = list(pattern.finditer(result))
        for m in reversed(matches):
            original = m.group(0)
            h = _hash_value(original)
            template = _MASK_TEMPLATES.get(pii_type, "***")
            replacement = template.format(hash=h, a=int(h) % 256, b=(int(h) // 256) % 256, c=int(h) % 100)
            result = result[:m.start()] + f"[{pii_type}:{replacement}]" + result[m.end():]
            count += 1
    return result, count


def synthesize_from_json(source: str | Path, target: str | Path) -> Dict:
    """Load JSON, mask all string values recursively, write masked copy.

    Returns: {"source": ..., "target": ..., "pii_masked": int, "keys_processed": int}
    """
    src = Path(source)
    tgt = Path(target)
    data = json.loads(src.read_text(encoding="utf-8"))

    total_masked = 0
    keys = 0

    def _walk(obj):
        nonlocal total_masked, keys
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys += 1
                if isinstance(v, str):
                    masked, n = mask_pii(v)
                    obj[k] = masked
                    total_masked += n
                elif isinstance(v, (dict, list)):
                    _walk(v)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, str):
                    masked, n = mask_pii(v)
                    obj[i] = masked
                    total_masked += n
                elif isinstance(v, (dict, list)):
                    _walk(v)

    _walk(data)
    tgt.parent.mkdir(parents=True, exist_ok=True)
    tgt.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"synthesized: {src.name} → {tgt.name} ({total_masked} PII masked, {keys} keys)")
    return {"source": str(src), "target": str(tgt), "pii_masked": total_masked, "keys_processed": keys}


def subset_json(source: str | Path, target: str | Path, max_records: int = 100) -> int:
    """Extract a random subset of records from a JSON array."""
    import random
    src = Path(source)
    tgt = Path(target)
    data = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(data, list):
        subset = random.sample(data, min(max_records, len(data)))
    elif isinstance(data, dict) and any(isinstance(v, list) for v in data.values()):
        subset = data.copy()
        for k, v in subset.items():
            if isinstance(v, list):
                subset[k] = random.sample(v, min(max_records, len(v)))
    else:
        subset = data
    tgt.parent.mkdir(parents=True, exist_ok=True)
    tgt.write_text(json.dumps(subset, indent=2, ensure_ascii=False), encoding="utf-8")
    count = len(subset) if isinstance(subset, list) else sum(len(v) for v in subset.values() if isinstance(v, list))
    logger.info(f"subset: {src.name} → {tgt.name} ({count} records)")
    return count


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Test data synthesis: PII mask + subset")
    p.add_argument("source", help="Source JSON file")
    p.add_argument("--target", help="Output path (default: source_synthesized.json)")
    p.add_argument("--subset", type=int, default=0, help="Max records for subset")
    args = p.parse_args()

    src = Path(args.source)
    tgt = Path(args.target) if args.target else src.parent / f"{src.stem}_synthesized.json"

    result = synthesize_from_json(src, tgt)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.subset > 0:
        subset_tgt = tgt.parent / f"{tgt.stem}_subset{args.subset}.json"
        n = subset_json(tgt, subset_tgt, args.subset)
        print(f"Subset: {n} records → {subset_tgt}")


if __name__ == "__main__":
    _cli()
