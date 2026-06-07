"""Thin entry point for PyInstaller-bundled Test-Agent backend.

Started by Electron main process as a child process.
Reads port from TAGENT_API_PORT env var (set by Electron).
"""

import os
import sys

import uvicorn


def main() -> None:
    port = int(os.getenv("TAGENT_API_PORT", "8800"))
    host = os.getenv("TAGENT_API_HOST", "127.0.0.1")

    # Stub LLM as default for offline-first desktop experience
    os.environ.setdefault("TAGENT_LLM_PROVIDER", "stub")
    os.environ.setdefault("TAGENT_LLM_PROVIDER_FALLBACK", "stub")

    uvicorn.run(
        "runtime.api.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
