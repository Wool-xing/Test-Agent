"""Tests for utils/security/api_security_scanner_v2.py.

Locks the rule: when every probe request fails, the scanner must report a
WARN "unable to scan" entry — zero findings must never silently read as
"API is clean".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.security.api_security_scanner_v2 import (  # noqa: E402
    check_excessive_data,
    check_mass_assignment,
)


@pytest.fixture(autouse=True)
def _broken_network(monkeypatch):
    """Every request raises — simulates target down / network partition."""

    def boom(*args, **kwargs):  # noqa: ARG001
        raise ConnectionError("target down")

    import requests

    monkeypatch.setattr(requests, "get", boom)
    monkeypatch.setattr(requests, "request", boom)


class TestScanFailureIsLoud:
    def test_excessive_data_all_failed_reports_warn(self):
        findings = check_excessive_data(
            "http://localhost:8800",
            [{"path": "/users", "method": "GET"}],
            user_token="t",
            admin_token="a",
        )
        assert findings, "all-requests-failed must produce a WARN entry"
        assert any("unable to scan" in f.get("finding", "") for f in findings)

    def test_mass_assignment_all_failed_reports_warn(self):
        findings = check_mass_assignment(
            "http://localhost:8800",
            [{"path": "/users", "method": "POST"}],
            user_token="t",
        )
        assert findings, "all-requests-failed must produce a WARN entry"
        assert any("unable to scan" in f.get("finding", "") for f in findings)
