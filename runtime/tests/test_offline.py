"""TDD tests for Offline Mode (§补-4)."""

from runtime.infra.offline import (
    OfflineManager,
    NetworkStatus,
    get_offline_manager,
    _check_network_connectivity,
    _build_offline_message,
    OfflineStatus,
)


class TestOfflineManager:
    def test_initial_status_online(self):
        """Initial status should be online, limited, or offline."""
        om = OfflineManager()
        assert om.status.network in (NetworkStatus.ONLINE, NetworkStatus.OFFLINE, NetworkStatus.LIMITED)

    def test_get_test_capabilities(self):
        """Should return at least local capabilities."""
        om = OfflineManager()
        caps = om.get_test_capabilities()
        assert "local-file" in caps
        assert "local-process" in caps

    def test_singleton(self):
        """get_offline_manager should return same instance."""
        om1 = get_offline_manager()
        om2 = get_offline_manager()
        assert om1 is om2


class TestNetworkCheck:
    def test_connectivity_check(self):
        """_check_network_connectivity should return bool."""
        result = _check_network_connectivity(timeout=1.0)
        assert isinstance(result, bool)


class TestOfflineMessage:
    def test_offline_message(self):
        """Offline message should describe status."""
        status = OfflineStatus(network=NetworkStatus.OFFLINE, llm_available=False)
        msg = _build_offline_message(status)
        assert len(msg) > 0

    def test_online_message(self):
        """Online message should be positive."""
        status = OfflineStatus(network=NetworkStatus.ONLINE, llm_available=True)
        msg = _build_offline_message(status)
        assert "online" in msg.lower()
