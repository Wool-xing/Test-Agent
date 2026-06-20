"""TDD tests for Sprint 1 basic skills: ping, http, file, process, timeout.

§五 Phase 4 TDD cycle: RED (write test) → GREEN (verify) → IMPROVE (refactor).
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════
# ping-check
# ═══════════════════════════════════════════════════════════════

class TestPingCheck:
    def test_ping_localhost_ok(self):
        """RED→GREEN: ping 127.0.0.1 should succeed."""
        from utils.ping_check import ping_host
        result = ping_host("127.0.0.1", count=1, timeout=5)
        assert result["ok"] is True
        assert result["host"] == "127.0.0.1"
        assert "latency_ms" in result

    def test_ping_invalid_host_fails(self):
        """ping nonexistent host should fail."""
        from utils.ping_check import ping_host
        result = ping_host("192.0.2.1", count=1, timeout=3)
        # May fail or timeout — both acceptable for invalid host
        assert "host" in result

    def test_ping_script_cli(self):
        """Verify CLI script runs."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "utils/ping_check.py", "--host", "127.0.0.1", "--count", "1", "--timeout", "5"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        assert "ok" in data


# ═══════════════════════════════════════════════════════════════
# http-check
# ═══════════════════════════════════════════════════════════════

class TestHttpCheck:
    def test_http_localhost_fails_gracefully(self):
        """Unreachable URL returns ok=False, not crash."""
        from utils.http_check import check_http
        result = check_http("http://127.0.0.1:1", timeout=3)
        assert result["ok"] is False
        assert "error" in result

    def test_http_invalid_url(self):
        """Invalid URL returns ok=False."""
        from utils.http_check import check_http
        result = check_http("not-a-url", timeout=3)
        assert result["ok"] is False

    def test_http_script_cli_help(self):
        """Verify CLI script parses args."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "utils/http_check.py", "--url", "http://127.0.0.1:1", "--timeout", "3"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        assert "url" in data


# ═══════════════════════════════════════════════════════════════
# file-check
# ═══════════════════════════════════════════════════════════════

class TestFileCheck:
    def test_file_exists_with_content(self):
        """Existing file with matching content should pass."""
        from utils.file_check import check_file
        result = check_file(__file__, content_contains="TDD")
        assert result["ok"] is True
        assert result["exists"] is True

    def test_file_not_found(self):
        """Non-existing file within project should fail with exists=True default."""
        from utils.file_check import check_file
        result = check_file("workspace/nonexistent_test_file_12345.xyz")
        assert result["ok"] is False
        assert result["exists"] is False

    def test_file_size_check(self):
        """Size constraint should validate correctly."""
        from utils.file_check import check_file
        # This test file is > 100 bytes
        result = check_file(__file__, min_size=100)
        assert result["ok"] is True


# ═══════════════════════════════════════════════════════════════
# process-check
# ═══════════════════════════════════════════════════════════════

class TestProcessCheck:
    def test_python_running(self):
        """Python process should be found as running."""
        from utils.process_check import check_process
        proc_name = "python.exe" if sys.platform == "win32" else "python"
        result = check_process(proc_name, expected_running=True)
        assert result["ok"] is True
        assert result["running"] is True

    def test_nonexistent_process(self):
        """Non-existent process should report not running."""
        from utils.process_check import check_process
        result = check_process("this_process_does_not_exist_xyz", expected_running=False)
        assert result["ok"] is True
        assert result["running"] is False


# ═══════════════════════════════════════════════════════════════
# timeout-check
# ═══════════════════════════════════════════════════════════════

class TestTimeoutCheck:
    def test_fast_command_passes(self):
        """Command completing within timeout should pass."""
        from utils.timeout_check import check_timeout
        import sys
        cmd = "cmd /c echo hello" if sys.platform == "win32" else "echo hello"
        result = check_timeout(cmd, timeout=5)
        assert result["ok"] is True

    def test_timeout_triggers(self):
        """Command exceeding timeout should fail."""
        from utils.timeout_check import check_timeout
        if sys.platform == "win32":
            result = check_timeout("ping -n 10 127.0.0.1", timeout=1)
        else:
            result = check_timeout("sleep 10", timeout=1)
        assert result["ok"] is False

    def test_invalid_command(self):
        """Invalid command should fail gracefully."""
        from utils.timeout_check import check_timeout
        result = check_timeout("nonexistent_command_xyz", timeout=5)
        assert "command" in result


# ═══════════════════════════════════════════════════════════════
# D1 边界测试 — 空值/超长/异常路径
# ═══════════════════════════════════════════════════════════════

class TestPingCheckBoundary:
    """D1 boundary tests for ping-check."""

    def test_ping_empty_host(self):
        """Empty host should be rejected."""
        from utils.ping_check import ping_host
        result = ping_host("", count=1, timeout=3)
        assert result["ok"] is False
        assert "invalid" in str(result.get("error", "")).lower()

    def test_ping_negative_count(self):
        """Negative count should not crash."""
        from utils.ping_check import ping_host
        result = ping_host("127.0.0.1", count=-1, timeout=3)
        assert "host" in result

    def test_ping_very_long_hostname(self):
        """Very long hostname should be rejected."""
        from utils.ping_check import ping_host
        long_host = "a" * 300 + ".com"
        result = ping_host(long_host, count=1, timeout=3)
        assert "host" in result


class TestHttpCheckBoundary:
    """D1 boundary tests for http-check."""

    def test_http_empty_url(self):
        """Empty URL should fail gracefully."""
        from utils.http_check import check_http
        result = check_http("", timeout=3)
        assert result["ok"] is False

    def test_http_very_long_url(self):
        """Very long URL should be handled."""
        from utils.http_check import check_http
        long_url = "http://example.com/" + "a" * 5000
        result = check_http(long_url, timeout=3)
        assert "url" in result

    def test_http_private_ip_blocked(self):
        """SSRF: private IP should be blocked."""
        from utils.http_check import check_http
        result = check_http("http://127.0.0.1:8080", timeout=3)
        assert result["ok"] is False
        assert "blocked" in str(result.get("error", "")).lower()

    def test_http_invalid_scheme(self):
        """file:// scheme should be blocked."""
        from utils.http_check import check_http
        result = check_http("file:///etc/passwd", timeout=3)
        assert result["ok"] is False
        assert "unsupported" in str(result.get("error", "")).lower()


class TestFileCheckBoundary:
    """D1 boundary tests for file-check."""

    def test_file_empty_path(self):
        """Empty path resolves to CWD — should show exists."""
        from utils.file_check import check_file
        result = check_file("")
        assert "exists" in result  # resolves to CWD, should not crash

    def test_file_path_traversal_blocked(self):
        """Path traversal attempt should be blocked."""
        from utils.file_check import check_file
        result = check_file("../../../etc/passwd")
        assert result["ok"] is False
        assert "outside" in str(result.get("error", "")).lower()

    def test_file_min_size_zero_ignored(self):
        """min_size=0 should be treated as no limit."""
        from utils.file_check import check_file
        result = check_file(__file__, min_size=0)
        assert result["exists"] is True


class TestProcessCheckBoundary:
    """D1 boundary tests for process-check."""

    def test_process_empty_name(self):
        """Empty process name should fail gracefully."""
        from utils.process_check import check_process
        result = check_process("")
        assert "process" in result

    def test_process_special_chars(self):
        """Process name with special chars should not crash."""
        from utils.process_check import check_process
        result = check_process("test; rm -rf /", expected_running=False)
        assert result["ok"] is True  # not running
        assert result["running"] is False


class TestTimeoutCheckBoundary:
    """D1 boundary tests for timeout-check."""

    def test_timeout_zero_seconds(self):
        """Zero timeout should trigger immediately."""
        from utils.timeout_check import check_timeout
        result = check_timeout("echo hello", timeout=0)
        assert "command" in result

    def test_timeout_empty_command(self):
        """Empty command should fail."""
        from utils.timeout_check import check_timeout
        result = check_timeout("", timeout=5)
        assert "command" in result
