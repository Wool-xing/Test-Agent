"""TDD tests for Test Execution Sandbox (§补-16)."""

from runtime.core.sandbox import (
    ProcessSandbox,
    SandboxConfig,
    SandboxLevel,
    SandboxResult,
    create_sandbox,
)


class TestProcessSandbox:
    def test_execute_echo(self):
        """Simple echo command should succeed."""
        sb = ProcessSandbox()
        result = sb.execute(["echo", "hello"])
        assert result.ok is True
        assert "hello" in result.stdout
        sb.cleanup()

    def test_execute_timeout(self):
        """Slow command should timeout."""
        sb = ProcessSandbox(SandboxConfig(time_limit_seconds=1))
        result = sb.execute(["sleep", "10"], timeout=1)
        assert result.timed_out is True
        sb.cleanup()

    def test_execute_failure(self):
        """Failing command should report error."""
        sb = ProcessSandbox()
        result = sb.execute(["python", "-c", "import sys; sys.exit(1)"])
        assert result.ok is False
        assert result.returncode == 1
        sb.cleanup()

    def test_work_dir_created(self):
        """Sandbox should create isolated work directory."""
        sb = ProcessSandbox()
        wd = sb.work_dir
        assert wd.exists()
        assert "test-agent-" in str(wd)
        sb.cleanup()
        assert not wd.exists()  # Original dir cleaned up

    def test_sandbox_config(self):
        """SandboxConfig should have sane defaults."""
        config = SandboxConfig()
        assert config.level == SandboxLevel.PROCESS
        assert config.memory_limit_mb == 256
        assert config.time_limit_seconds == 300
        assert config.network_enabled is False

    def test_create_sandbox_factory(self):
        """Factory should create process sandbox."""
        sb = create_sandbox(SandboxLevel.PROCESS)
        assert isinstance(sb, ProcessSandbox)
        sb.cleanup()

    def test_create_container_not_implemented(self):
        """L2/L3 should raise not implemented."""
            with pytest.raises(NotImplementedError): sandbox.create_container()
        import pytest
        with pytest.raises(NotImplementedError):
            create_sandbox(SandboxLevel.CONTAINER)
        with pytest.raises(NotImplementedError):
            create_sandbox(SandboxLevel.VM)
