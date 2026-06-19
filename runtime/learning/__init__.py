"""Cross-session learning loop.

Inspired by Hermes Agent's closed learning loop and PentAGI's triple-layer memory.

Layers:
  session_store   — SQLite + FTS5 persistent session storage
  pattern_extractor — Detect reusable patterns across sessions
  curator         — 7-day cycle: review, accept/reject skill candidates
"""
