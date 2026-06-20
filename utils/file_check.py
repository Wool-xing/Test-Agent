"""file-check skill: file existence/size/content validation."""
import argparse, sys, json, os
from pathlib import Path


def check_file(path: str, exists: bool = True, min_size: int = 0, max_size: int = 0,
               content_contains: str = "", content_regex: str = "") -> dict:
    p = Path(path)
    if not p.exists():
        return {"ok": not exists, "path": path, "exists": False, "error": "file not found" if exists else ""}
    size = p.stat().st_size
    checks = []
    if min_size and size < min_size:
        checks.append({"check": "min_size", "expected": f">{min_size}", "actual": str(size), "pass": False})
    if max_size and size > max_size:
        checks.append({"check": "max_size", "expected": f"<{max_size}", "actual": str(size), "pass": False})
    if content_contains:
        text = p.read_text(encoding="utf-8", errors="replace")
        found = content_contains in text
        checks.append({"check": "content_contains", "expected": content_contains[:50], "pass": found})
    ok = all(c.get("pass", True) for c in checks)
    return {"ok": ok, "path": path, "exists": True, "size": size, "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--min-size", type=int, default=0, dest="min_size")
    parser.add_argument("--max-size", type=int, default=0, dest="max_size")
    parser.add_argument("--content-contains", default="", dest="content_contains")
    args = parser.parse_args()
    result = check_file(args.path, min_size=args.min_size, max_size=args.max_size, content_contains=args.content_contains)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
