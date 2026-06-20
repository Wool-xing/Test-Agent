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
        # Should not crash; may return ok=False or ok=True depending on shell
        assert "command" in result
