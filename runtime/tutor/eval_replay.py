"""Eval capture + replay · gbrain §1.6 派生.

opt-in via TAGENT_EVAL_CAPTURE=1. PII-scrubbed routing queries land in
`workspace/learning/eval_candidates.jsonl`. Replay computes 3 metrics:
  - Jaccard@k between captured and current routed expert lists
  - top-1 stability
  - latency Δ (ms)

Off by default — production users never accumulate data without consent.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.config.settings import get_settings


def _capture_path() -> Path:
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "learning" / "eval"
    d.mkdir(parents=True, exist_ok=True)
    return d / "eval_candidates.jsonl"


# PII scrub — single source of truth (gbrain §1.9)
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
    (re.compile(r"\b1[3-9]\d{9}\b"), "<PHONE-CN>"),
    (re.compile(r"\b\+?[1-9]\d{6,14}\b"), "<PHONE>"),
    (re.compile(r"\b(\d{3}-?\d{2}-?\d{4})\b"), "<SSN>"),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), "<HASH>"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "<API-KEY>"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "<CARD>"),
]


def scrub_pii(text: str) -> str:
    for pat, sub in PII_PATTERNS:
        text = pat.sub(sub, text)
    return text


def is_capture_enabled() -> bool:
    return os.getenv("TAGENT_EVAL_CAPTURE", "0") in ("1", "true", "yes")


def capture(query: str, *, routed_experts: list[str], target_type: str, confidence: float, elapsed_ms: int) -> None:
    """Append one capture row. No-op if not enabled."""
    if not is_capture_enabled():
        return
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "query_scrubbed": scrub_pii(query)[:500],
        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
        "routed_experts": routed_experts,
        "target_type": target_type,
        "confidence": confidence,
        "elapsed_ms": elapsed_ms,
    }
    with _capture_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_captures(limit: int | None = None) -> list[dict]:
    p = _capture_path()
    if not p.is_file():
        return []
    rows: list[dict] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if limit and len(rows) >= limit:
                break
    return rows


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def replay(captures: list[dict] | None = None, *, max_replay: int = 50) -> dict[str, Any]:
    """Re-run captured queries through current router; return 3 metrics."""
    from runtime.api.deps import Kernel
    from runtime.api.parsers import parse_text

    captures = captures or load_captures(limit=max_replay)
    if not captures:
        return {"replayed": 0, "note": "no captures"}

    k = Kernel()
    jaccards: list[float] = []
    top1_match = 0
    latency_deltas: list[int] = []

    for cap in captures[:max_replay]:
        text = cap.get("query_scrubbed", "")
        if not text:
            continue
        art = parse_text(text)
        start = time.monotonic()
        _, decision = k.submit(art, persist=False)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        current_experts = [n.name for n in decision.dag]
        captured_experts = cap.get("routed_experts", [])
        jaccards.append(_jaccard(captured_experts, current_experts))
        if captured_experts and current_experts and captured_experts[0] == current_experts[0]:
            top1_match += 1
        latency_deltas.append(elapsed_ms - cap.get("elapsed_ms", elapsed_ms))

    n = len(jaccards)
    return {
        "replayed": n,
        "mean_jaccard": sum(jaccards) / max(n, 1),
        "top1_stability": top1_match / max(n, 1),
        "mean_latency_delta_ms": sum(latency_deltas) / max(len(latency_deltas), 1) if latency_deltas else 0.0,
    }
