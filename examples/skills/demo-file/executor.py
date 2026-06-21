"""Demo File Check executor."""

from pathlib import Path


def execute(params: dict, ctx) -> dict:
    path = params.get("path", "")
    if not path:
        return {"status": "error", "summary": "Missing required parameter: path", "details": {}, "checks": [], "error": "FILE-001"}

    p = Path(path)
    if not p.exists():
        return {"status": "fail", "summary": f"File not found: {path}", "details": {}, "checks": [{"name": "Exists", "expected": True, "actual": False, "pass": False}], "error": None}

    size = p.stat().st_size
    checks = [{"name": "Exists", "expected": True, "actual": True, "pass": True}]
    expected_size = params.get("min_size")
    if expected_size is not None:
        ok = size >= int(expected_size)
        checks.append({"name": "Min Size", "expected": f">={expected_size}B", "actual": f"{size}B", "pass": ok})

    expected_content = params.get("contains")
    if expected_content:
        content = p.read_text(encoding="utf-8", errors="replace")
        ok = expected_content in content
        checks.append({"name": "Contains", "expected": expected_content, "actual": "found" if ok else "not found", "pass": ok})

    all_pass = all(c["pass"] for c in checks)
    return {"status": "pass" if all_pass else "fail", "summary": f"Checked {path} ({size}B)", "details": {"path": str(p), "size_bytes": size}, "checks": checks, "error": None}
