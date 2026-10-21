from __future__ import annotations

import os


def resolve_model_mode(requested: str | None = None) -> str:
    """Return 'fake', 'openai', or 'anthropic'.

    Default is fake unless OPENAI_API_KEY / ANTHROPIC_API_KEY is set, or
    HARNESS_MODEL overrides.
    """
    explicit = (requested or os.environ.get("HARNESS_MODEL") or "").strip().lower()
    if explicit in {"fake", "openai", "anthropic"}:
        return explicit
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "fake"


def model_id_for_mode(mode: str) -> str:
    if mode == "openai":
        return os.environ.get("HARNESS_OPENAI_MODEL", "gpt-4o-mini")
    if mode == "anthropic":
        return os.environ.get("HARNESS_ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    return "fake"
