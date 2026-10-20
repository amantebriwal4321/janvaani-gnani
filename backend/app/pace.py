"""Short spoken beats that make a turn feel quick. Eligibility is not decided here."""

from __future__ import annotations

import re

from app.dialogue import say

_BREAK = re.compile(r"(?<=[।.!?])\s+")

# Speak a one-line acknowledgement if the real answer is still being built.
FILLER_AFTER = 0.32


def split_spoken(text: str) -> list[str]:
    """First sentence first, so Timbre can start while the rest is still rendering."""
    clean = " ".join((text or "").split())
    if not clean:
        return []
    parts = [part.strip() for part in _BREAK.split(clean) if part.strip()]
    return parts or [clean]


def filler_line(language: str) -> str:
    return say("filler", language or "hi")


def recover_message() -> str:
    return "I lost the listening line for a moment. Speak again, or type. Nothing you already said is lost."
