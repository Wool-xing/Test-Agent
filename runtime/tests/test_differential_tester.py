"""Tests for utils/testing/differential_tester.py.

Locks the rule: two 200s whose bodies fail JSON parsing must NEVER read as
"identical" — parse failure is a divergence, recorded as json_parse_error.
"""

from __future__ import annotations

import http.server
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.testing.differential_tester import compare_apis  # noqa: E402


class _Handler(http.server.BaseHTTPRequestHandler):
    body = b"{}"
    content_type = "application/json"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", self.content_type)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):  # noqa: ARG002
        pass


@pytest.fixture
def servers():
    """Two real HTTP servers with configurable response bodies."""
    started = []
    for body, ctype in [(b"not-json-at-all", "text/plain"), (b"still-not-json", "text/plain")]:
        handler = type("H", (_Handler,), {"body": body, "content_type": ctype})
        srv = http.server.HTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append((srv, srv.server_address[1]))
    yield started
    for srv, _ in started:
        srv.shutdown()


def _url(servers, idx):
    return f"http://127.0.0.1:{servers[idx][1]}"


class TestJsonParseFailureIsDivergence:
    def test_parse_failure_not_identical(self, servers):
        """Both 200 + invalid JSON on one side → divergence, not identical."""
        report = compare_apis(
            _url(servers, 0), _url(servers, 1), [{"path": "x", "method": "GET"}]
        )
        assert report.identical == 0
        assert report.diverged == 1
        assert report.results[0].divergence_type == "json_parse_error"


class TestValidJsonStillWorks:
    def test_same_json_is_identical(self):
        class J(_Handler):
            body = json.dumps({"ok": True, "n": 1}).encode()

        srv = http.server.HTTPServer(("127.0.0.1", 0), J)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            report = compare_apis(base, base, [{"path": "x", "method": "GET"}])
            assert report.identical == 1
        finally:
            srv.shutdown()

    def test_different_json_diverges(self, servers):
        """Non-200 differences still detected as before."""

        class A(_Handler):
            body = json.dumps({"v": 1}).encode()

        class B(_Handler):
            body = json.dumps({"v": 2}).encode()

        sa = http.server.HTTPServer(("127.0.0.1", 0), A)
        sb = http.server.HTTPServer(("127.0.0.1", 0), B)
        threading.Thread(target=sa.serve_forever, daemon=True).start()
        threading.Thread(target=sb.serve_forever, daemon=True).start()
        try:
            report = compare_apis(
                f"http://127.0.0.1:{sa.server_address[1]}",
                f"http://127.0.0.1:{sb.server_address[1]}",
                [{"path": "x", "method": "GET"}],
            )
            assert report.identical == 0
        finally:
            sa.shutdown()
            sb.shutdown()
