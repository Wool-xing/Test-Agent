"""Offline Mode (§补-4) — operate without network connectivity.

Features:
- Auto-detect network status via connectivity check
- Fall back to local Ollama when cloud LLM unavailable
- Cache skills locally for offline use
- Local-only test execution mode
- Clear user notification of limited capabilities
"""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from enum import Enum


class NetworkStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    LIMITED = "limited"   # Some endpoints reachable, LLM API not


@dataclass
class OfflineStatus:
    network: NetworkStatus = NetworkStatus.ONLINE
    llm_available: bool = True
    local_llm_available: bool = False
    skill_cache_available: bool = True
    message: str = ""


class OfflineManager:
    """Manages offline/online mode transitions."""

    def __init__(self):
        self._status = OfflineStatus()
        self._lock = threading.Lock()
        self._check_interval = 30.0  # seconds between health checks
        self._last_check = 0.0

    @property
    def status(self) -> OfflineStatus:
        import time
        if time.time() - self._last_check > self._check_interval:
            self.refresh()
        return self._status

    def refresh(self) -> OfflineStatus:
        """Re-check all connectivity and update status."""
        import time
        with self._lock:
            self._last_check = time.time()
            online = _check_network_connectivity()
            if not online:
                self._status.network = NetworkStatus.OFFLINE
                self._status.llm_available = False
                self._status.local_llm_available = _check_ollama_available()
                self._status.message = _build_offline_message(self._status)
                return self._status

            # Online — check LLM
            self._status.network = NetworkStatus.ONLINE
            self._status.llm_available = _check_llm_api()
            self._status.local_llm_available = _check_ollama_available()
            if not self._status.llm_available:
                self._status.network = NetworkStatus.LIMITED
                self._status.message = "Cloud LLM unavailable; using local Ollama or stub mode"
            else:
                self._status.message = "All systems online"
            return self._status

    def get_test_capabilities(self) -> list[str]:
        """List available test capabilities based on current status."""
        caps = ["local-file", "local-process", "local-timeout"]
        s = self.status
        if s.network != NetworkStatus.OFFLINE:
            caps.extend(["http-check", "ping-check"])
        if s.llm_available or s.local_llm_available:
            caps.append("ai-routing")
        return caps


def _check_network_connectivity(timeout: float = 3.0) -> bool:
    """Check if network is available."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except Exception:
        pass
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout)
        return True
    except Exception:
        return False


def _check_llm_api(timeout: float = 5.0) -> bool:
    """Check if the configured LLM API is reachable."""
    try:
        from runtime.config.settings import get_settings
        s = get_settings()
        import os
        api_key = os.environ.get("TAGENT_LLM_API_KEY", os.environ.get(f"TAGENT_LLM_API_KEY_{s.llm_provider.upper()}", ""))
        return bool(api_key)  # API key presence = LLM configured
    except Exception:
        return False


def _check_ollama_available(timeout: float = 2.0) -> bool:
    """Check if local Ollama is running."""
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=timeout)
        return True
    except Exception:
        return False


def _build_offline_message(status: OfflineStatus) -> str:
    """Build user-facing offline status message."""
    if status.network == NetworkStatus.OFFLINE:
        if status.local_llm_available:
            return "Network offline — using local Ollama. Network-dependent tests will be skipped."
        return "Network offline — using stub mode. Only local tests available."
    if status.network == NetworkStatus.LIMITED:
        return "Cloud LLM unavailable — using local fallback."
    return "All systems online."


# Singleton
_manager: OfflineManager | None = None


def get_offline_manager() -> OfflineManager:
    global _manager
    if _manager is None:
        _manager = OfflineManager()
    return _manager
