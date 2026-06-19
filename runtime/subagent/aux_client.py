"""Auxiliary LLM client (never touches main session prompt cache).

Subagents and curator share NOTHING with the main routing path beyond raw model API.
Different env vars (TAGENT_AUX_*) so users can pin a cheaper/faster aux model.
"""

from __future__ import annotations

import os

from runtime.router.llm_client import LLMClient


def aux_client() -> LLMClient:
    """Return an aux-only LLMClient with independent provider/model overrides."""
    provider = os.getenv("TAGENT_AUX_PROVIDER") or os.getenv("TAGENT_LLM_PROVIDER", "claude")
    fallback = os.getenv("TAGENT_AUX_PROVIDER_FALLBACK") or os.getenv("TAGENT_LLM_PROVIDER_FALLBACK", "ollama")
    # Note: LLMClient reads model from settings; for now we just pin provider isolation.
    return LLMClient(provider=provider, fallback=fallback)
