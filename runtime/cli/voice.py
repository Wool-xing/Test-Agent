"""Voice interaction — text-to-speech for test results (P3 #23).

Uses platform-native TTS: Windows SAPI, macOS say, Linux espeak.
Falls back gracefully if no TTS engine available.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def _windows_speak(text: str) -> bool:
    """Windows SAPI TTS via win32com."""
    try:
        import win32com.client
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Speak(text[:500])
        return True
    except ImportError:
        return False
    except Exception:
        return False


def _mac_speak(text: str) -> bool:
    """macOS say command."""
    try:
        subprocess.run(["say", text[:500]], timeout=15, capture_output=True)
        return True
    except Exception:
        return False


def _linux_speak(text: str) -> bool:
    """Linux espeak."""
    try:
        subprocess.run(["espeak", text[:500]], timeout=15, capture_output=True)
        return True
    except Exception:
        return False


def speak(text: str) -> bool:
    """Read text aloud using platform TTS. Returns True if speech was attempted."""
    if not text.strip():
        return False

    if sys.platform == "win32":
        return _windows_speak(text)
    elif sys.platform == "darwin":
        return _mac_speak(text)
    else:
        return _linux_speak(text)


def announce_result(summary: dict[str, Any]) -> str | None:
    """Generate a spoken summary of test results. Returns the spoken text."""
    total = summary.get("total", 0)
    succ = summary.get("succeeded", 0)
    fail = summary.get("failed", 0)

    if total == 0:
        return None

    if fail == 0:
        text = f"All {succ} tests passed."
    else:
        text = f"{succ} passed, {fail} failed out of {total}."

    speak(text)
    return text
