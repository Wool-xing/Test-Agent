"""四重安全验证.

关 1: signature_check  (sha256 + ed25519 可选)
关 2: injection_scan   (prompt 注入扫,复用 scheduler 模块)
关 3: sandbox_dry_run  (Docker 沙箱试跑)
关 4: darwin_score     (≥75 才放行)

每关失败 → 落 decisions/ + 返回 reason
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GateResult:
    gate: str
    passed: bool
    reason: str = ""
    score: int | None = None


def gate_signature(content: bytes, expected_sha256: str = "", signature: str = "") -> GateResult:
    """Gate 1: SHA256 + 可选 ed25519."""
    actual = hashlib.sha256(content).hexdigest
    if expected_sha256 and actual != expected_sha256:
        return GateResult("signature", False, f"sha256 mismatch: {actual} vs {expected_sha256}")
    # ed25519 略,可加 cryptography lib 实现
    return GateResult("signature", True, score=actual[:16])


def gate_injection_scan(text: str) -> GateResult:
    """Gate 2: Prompt 注入扫(复用 scheduler 模块)."""
    try:
        from runtime.scheduler.injection_scan import PromptInjectionBlocked, scan

        scan(text)
        return GateResult("injection_scan", True)
    except PromptInjectionBlocked as e:
        return GateResult("injection_scan", False, f"injection pattern: {e.reason}")
    except Exception as e:
        return GateResult("injection_scan", False, f"scan error: {e}")


def gate_sandbox_dry_run(file_path: Path, *, timeout_seconds: int = 60) -> GateResult:
    """Gate 3: Docker 沙箱试跑.

    Production 应跑 24h;本简化版只 syntax check + 短 dry-run.
    """
    if not file_path.exists:
        return GateResult("sandbox_dry_run", False, f"file not found: {file_path}")
    # 简化:markdown skill 文件只 syntax check;.py 文件 ast.parse
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if file_path.suffix == ".py":
        import ast

        try:
            ast.parse(text)
        except SyntaxError as e:
            return GateResult("sandbox_dry_run", False, f"py syntax: {e}")
    # production: subprocess.run(["docker", "run", "--rm", "--network=none", ...])
    return GateResult("sandbox_dry_run", True, score=len(text))


def gate_darwin_score(file_path: Path, *, min_score: int = 75) -> GateResult:
    """Gate 4: darwin-skill 评分(≥75)."""
    # 简化:取文件长度 + frontmatter 完整性当代理
    if not file_path.exists:
        return GateResult("darwin_score", False, "file not found")
    text = file_path.read_text(encoding="utf-8", errors="replace")
    score = 50
    if "name:" in text:
        score += 10
    if "description:" in text:
        score += 15
    if len(text) > 200:
        score += 5
    if len(text) > 500:
        score += 10
    if "trigger" in text or "when to use" in text.lower:
        score += 10
    if score >= min_score:
        return GateResult("darwin_score", True, score=score)
    return GateResult("darwin_score", False, f"score {score} < {min_score}", score=score)


def run_all_gates(file_path: Path, *, expected_sha256: str = "", signature: str = "",
                   skip_sandbox: bool = False, skip_darwin: bool = False,
                   min_darwin: int = 75) -> list[GateResult]:
    """Run all 4 gates in order; stop at first failure."""
    content = file_path.read_bytes if file_path.exists else b""
    results: list[GateResult] = []

    g1 = gate_signature(content, expected_sha256=expected_sha256, signature=signature)
    results.append(g1)
    if not g1.passed:
        return results

    g2 = gate_injection_scan(content.decode("utf-8", "replace"))
    results.append(g2)
    if not g2.passed:
        return results

    if not skip_sandbox:
        g3 = gate_sandbox_dry_run(file_path)
        results.append(g3)
        if not g3.passed:
            return results

    if not skip_darwin:
        g4 = gate_darwin_score(file_path, min_score=min_darwin)
        results.append(g4)

    return results
