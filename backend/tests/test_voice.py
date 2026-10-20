"""Filler beats, sentence-sized speech, and the scripted demo household."""

import asyncio

from fastapi.testclient import TestClient

from app.demo import DEMO_SCRIPT
from app.engine import Brain
from app.main import app
from app.pace import filler_line, recover_message, split_spoken
from app.session import SESSIONS, CallSession
from tests.test_rules import _until


def test_filler_lines_stay_short_in_every_language():
    for language in ("hi", "hi-en", "en", "kn", "te", "ta", "mr", "bn", "ml", "zz"):
        line = filler_line(language)
        assert line
        assert len(line) < 80
        assert "aadhaar" not in line.casefold()


def test_recover_message_does_not_blame_the_caller():
    text = recover_message()
    assert "lost" in text.casefold()
    assert "GNANI" not in text
    assert "traceback" not in text.casefold()


def test_split_spoken_puts_the_first_sentence_first():
    parts = split_spoken("नमस्ते। मैं जनवाणी हूँ। आगे बताइए।")
    assert parts[0] == "नमस्ते।"
    assert parts[1] == "मैं जनवाणी हूँ।"
    assert len(parts) == 3
    assert split_spoken("   ") == []
    assert split_spoken("one line without a stop") == ["one line without a stop"]
    assert split_spoken("Ready.  Carry the papers.") == ["Ready.", "Carry the papers."]


def test_demo_script_reaches_a_ready_slip():
    brain = Brain()

    async def run():
        brain.set_language("hi")
        for turn in DEMO_SCRIPT:
            if turn.language:
                brain.set_language(turn.language)
            await brain.utterance(turn.text, None)
        snap = brain.snapshot()
        assert snap["slip"] == "ready"
        assert snap["user_turns"] == len(DEMO_SCRIPT)
        assert any(row["field"] == "district" and row["value"] == "Kolar" for row in snap["rows"])
        assert any(item["id"] == "pm_kisan" and item["status"] == "qualify" for item in snap["matches"])
        assert "PM-KISAN" in snap["share_text"]

    asyncio.run(run())


def test_turn_marks_thinking_before_the_snapshot(monkeypatch):
    monkeypatch.setattr("app.config.settings.gnani_api_key", "")
    monkeypatch.setattr("app.config.settings.llm_base_url", "")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/call") as ws:
            ws.send_json({"type": "start", "language": "en"})
            _until(ws, lambda message: message.get("type") == "speak")
            ws.send_json({"type": "utterance", "text": "I farm two acres in Kolar"})
            seen: list[str] = []
            for _ in range(20):
                message = ws.receive_json()
                if message.get("type") == "status" and message.get("phase") == "thinking":
                    seen.append("thinking")
                elif message.get("type") == "state" and message["state"]["user_turns"] >= 1:
                    seen.append("state")
                    break
            assert seen[0] == "thinking"
            assert "state" in seen
            assert seen.index("thinking") < seen.index("state")


def test_slow_turn_acknowledges_before_the_answer(monkeypatch):
    monkeypatch.setattr("app.config.settings.gnani_api_key", "")
    monkeypatch.setattr("app.config.settings.llm_base_url", "")
    monkeypatch.setattr("app.session.FILLER_AFTER", 0.05)
    original = Brain.utterance

    async def slow(self, text, llm):
        await asyncio.sleep(0.2)
        return await original(self, text, llm)

    monkeypatch.setattr(Brain, "utterance", slow)
    with TestClient(app) as client:
        with client.websocket_connect("/ws/call") as ws:
            ws.send_json({"type": "start", "language": "hi"})
            _until(ws, lambda message: message.get("type") == "speak")
            ws.send_json({"type": "utterance", "text": "haan"})
            kinds: list[str] = []
            for _ in range(24):
                message = ws.receive_json()
                kinds.append(message.get("type"))
                if message.get("type") == "state" and message["state"]["user_turns"] >= 1:
                    break
            assert "filler" in kinds
            assert kinds.index("filler") < kinds.index("state")


def test_barge_without_notify_still_cuts_audio():
    class Transport:
        name = "web"

        def __init__(self) -> None:
            self.cleared = 0
            self.messages: list[dict] = []

        async def send_json(self, data: dict) -> None:
            self.messages.append(data)

        async def send_pcm(self, pcm: bytes) -> None:
            return None

        async def clear_playback(self) -> None:
            self.cleared += 1

        async def flush(self) -> None:
            return None

    async def run():
        transport = Transport()
        session = CallSession(transport)
        try:
            session.speaking = True
            await session.barge(notify=False)
            assert transport.cleared == 1
            assert session.speaking is False
            assert not any(item.get("barged") for item in transport.messages)
            await session.barge()
            assert transport.cleared == 1
        finally:
            SESSIONS.pop(session.brain.session_id, None)

    asyncio.run(run())
