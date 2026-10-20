"""One scripted household so a demo video can be recorded without a microphone."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoTurn:
    text: str
    language: str | None = None


# The Kolar farmer from the challenge script, then the three CSC checks.
DEMO_SCRIPT: tuple[DemoTurn, ...] = (
    DemoTurn(
        "Main Kolar ke paas ek gaon se hoon, do acre mein tamatar ugata hoon, "
        "umar pentalees saal. Is baar baarish se fasal kharab ho gayi. "
        "BPL card hai, pitaji bahattar saal ke hain.",
        "hi",
    ),
    DemoTurn("nahi, naam alag likha hai"),
    DemoTurn("haan"),
    DemoTurn("haan"),
)

DEMO_LABEL = "Kolar farmer"
