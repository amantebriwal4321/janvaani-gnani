"""Request shapes and Prisma messages. No network."""

import asyncio
import json
import struct
import time

from app.gnani import (
    STTEvent,
    STTStream,
    parse_stt_message,
    parse_wav,
    stt_code,
    stt_form,
    stt_ws_headers,
    tts_body,
    tts_code,
)
from app.languages import STT_CODE
from app.session import SESSIONS, CallSession


def _wav(pcm: bytes, rate: int = 16000) -> bytes:
    fmt = struct.pack("<HHIIHH", 1, 1, rate, rate * 2, 2, 16)
    data_size = len(pcm)
    return (
        b"RIFF"
        + struct.pack("<I", 36 + data_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + struct.pack("<I", data_size)
        + pcm
    )


def test_stt_codes_are_in_forms_and_hinglish_is_indic_auto():
    assert "hi-en" not in STT_CODE.values()
    for code in STT_CODE.values():
        assert code.endswith("-IN"), code
    assert stt_code("kn", locked=True) == "kn-IN"
    assert stt_code("hi", locked=True) == "hi-IN"
    assert stt_code("hi-en", locked=True) == "indic-auto"
    assert stt_code("hi", locked=False) == "indic-auto"
    assert stt_code("auto") == "indic-auto"
    assert stt_form("te") == {"language_code": "te-IN"}
    assert tts_code("hi") == "hi-IN"
    assert tts_code("hi-en") == "hi-en"
    assert tts_code("kn") == "kn-IN"


def test_tts_body_matches_the_live_fields():
    body = tts_body("नमस्ते", "hi")
    assert set(body) == {"text", "voice", "model", "language", "audio_config"}
    assert body["language"] == "hi-IN"
    assert body["audio_config"] == {"sample_rate": 8000, "encoding": "linear_pcm", "container": "wav"}
    mulaw = tts_body("नमस्ते", "hi", "mulaw")
    assert mulaw["audio_config"] == {"container": "mulaw"}
    assert tts_code("en") == "en-IN"
    english = tts_body("Hello", "en")
    assert english["language"] == "en-IN"
    assert english["voice"] == body["voice"]


def test_english_tts_voice_override(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "gnani_tts_voice_en", "en-desk")
    assert tts_body("Hello", "en")["voice"] == "en-desk"
    assert tts_body("नमस्ते", "hi")["voice"] != "en-desk"


def test_stt_websocket_headers_match_the_live_socket():
    headers = stt_ws_headers("hi-IN")
    assert set(headers) == {
        "x-api-key-id",
        "lang_code",
        "x-sample-rate",
        "x-min-silence-ms",
        "x-bias-list",
        "x-bias-score",
    }
    assert headers["lang_code"] == "hi-IN"
    assert headers["x-sample-rate"] == "8000"
    assert headers["x-min-silence-ms"] == "400"
    assert headers["x-bias-score"] == "1.0"
    words = json.loads(headers["x-bias-list"])
    assert "Pakur" in words
    assert "Jharkhand" in words
    assert all(word.isalpha() and word.isascii() for word in words)


def test_prisma_messages():
    assert parse_stt_message({"type": "connected", "message": "ready"}) is None
    start = parse_stt_message({"type": "speech_start", "utterance_id": "u1"})
    assert start == STTEvent(type="speech_start", utterance_id="u1")
    partial = parse_stt_message({"type": "transcript", "text": "नम", "is_final": False, "segment_index": 1})
    assert partial is None
    final = parse_stt_message(
        {"type": "transcript", "text": "नमस्ते", "is_final": True, "segment_index": 1, "utterance_id": "u1"}
    )
    assert final is not None
    assert final.text == "नमस्ते"
    assert final.segment_index == 1
    assert final.is_final is True
    assert final.language == ""
    tagged = parse_stt_message(
        {"type": "transcript", "text": "hello", "is_final": True, "language_code": "en-IN"}
    )
    assert tagged is not None and tagged.language == "en-IN"
    nested = parse_stt_message(
        {"type": "transcript", "text": "ನಮಸ್ಕಾರ", "is_final": True, "metadata": {"detected_language": "kn-IN"}}
    )
    assert nested is not None and nested.language == "kn-IN"


def test_wav_strips_and_raw_mulaw_passes_through():
    pcm = b"\x00\x01" * 8
    audio, rate = parse_wav(_wav(pcm, 16000))
    assert rate == 16000
    assert audio == pcm
    raw = b"\xff\xff\x7f"
    same, assumed = parse_wav(raw)
    assert same == raw
    assert assumed == 8000


def test_frames_are_paced_at_64_ms():
    class FakeSocket:
        def __init__(self) -> None:
            self.sent: list[tuple[float, bytes]] = []

        async def send(self, frame: bytes) -> None:
            self.sent.append((time.monotonic(), frame))

    async def run():
        stream = STTStream("hi", locked=True)
        stream.ws = FakeSocket()
        stream._buffer.extend(b"\x01\x00" * 1024)
        task = asyncio.create_task(stream._pump())
        await asyncio.sleep(0.16)
        stream._closed = True
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return stream.ws.sent

    sent = asyncio.run(run())
    assert len(sent) >= 2
    assert all(len(frame) == 1024 for _, frame in sent)
    gap = sent[1][0] - sent[0][0]
    assert 0.05 <= gap <= 0.09


def test_speech_start_barges_in():
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
            await session.on_stt_event(STTEvent(type="speech_start", utterance_id="u9"))
            assert transport.cleared == 1
            assert session.speaking is False
            assert any(item.get("barged") for item in transport.messages)
        finally:
            SESSIONS.pop(session.brain.session_id, None)

    asyncio.run(run())
