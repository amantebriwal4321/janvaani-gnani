"""Gnani Prisma STT and Timbre TTS. No other speech vendor is called.

Shapes match a live check against https://api.vachana.ai on 2026-10-20:
REST STT is multipart audio_file + language_code. REST TTS returns the audio
bytes themselves. The realtime socket takes 1,024-byte PCM frames every 64 ms
and speaks connected, speech_start, and transcript.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import websockets

from app.audio import FRAME_BYTES, downsample_pcm16
from app.config import settings
from app.languages import STT_CODE, TTS_CODE

FRAME_INTERVAL = 0.064  # 512 samples at 8 kHz


def _ws_base() -> str:
    base = settings.gnani_base_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://") :]
    if base.startswith("http://"):
        return "ws://" + base[len("http://") :]
    return base


def stt_code(language: str, locked: bool = True) -> str:
    """Prisma language. Hinglish has no code; auto-detect uses indic-auto."""
    if not locked or language in ("", "auto", "hi-en"):
        return "indic-auto"
    return STT_CODE.get(language, "indic-auto")


def tts_code(language: str) -> str:
    if language in ("", "auto"):
        return "hi-IN"
    return TTS_CODE.get(language, "hi-IN")


def stt_form(language: str, locked: bool = True) -> dict[str, str]:
    return {"language_code": stt_code(language, locked=locked)}


def stt_ws_headers(lang_code: str) -> dict[str, str]:
    """Headers from the socket that transcribed 8 kHz audio."""
    return {
        "x-api-key-id": settings.gnani_api_key,
        "lang_code": lang_code,
        "x-sample-rate": "8000",
        "x-min-silence-ms": "400",
    }


def tts_audio_config(container: str = "wav", sample_rate: int = 8000) -> dict:
    # container "mulaw" alone: raw 8 kHz G.711, no RIFF header.
    if container == "mulaw":
        return {"container": "mulaw"}
    return {
        "sample_rate": sample_rate,
        "encoding": "linear_pcm",
        "container": container,
    }


def tts_body(text: str, language: str, container: str = "wav", sample_rate: int = 8000) -> dict:
    return {
        "text": text,
        "voice": settings.gnani_tts_voice,
        "model": settings.gnani_tts_model,
        "language": tts_code(language),
        "audio_config": tts_audio_config(container, sample_rate),
    }


def parse_wav(data: bytes) -> tuple[bytes, int]:
    """PCM payload and sample rate. Non-RIFF bytes pass through as 8 kHz PCM."""
    if len(data) < 44 or not data.startswith(b"RIFF"):
        return data, 8000
    rate = 8000
    pcm = b""
    offset = 12
    while offset + 8 <= len(data):
        chunk = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        start = offset + 8
        body = data[start : start + size]
        if chunk == b"fmt " and len(body) >= 8:
            rate = int.from_bytes(body[4:8], "little") or 8000
        elif chunk == b"data":
            pcm = body
            break
        offset = start + size + (size % 2)
    return pcm or data[44:], rate


@dataclass
class STTEvent:
    type: str
    text: str = ""
    is_final: bool = True
    segment_index: int | None = None
    utterance_id: str = ""


def parse_stt_message(data: dict) -> STTEvent | None:
    """Map one Prisma message. `connected` is ignored. Partials are dropped."""
    kind = data.get("type")
    if kind == "speech_start":
        return STTEvent(type="speech_start", utterance_id=str(data.get("utterance_id") or ""))
    if kind == "transcript":
        text = str(data.get("text") or "").strip()
        is_final = bool(data.get("is_final", True))
        if not text or not is_final:
            return None
        raw_index = data.get("segment_index")
        index: int | None
        try:
            index = int(raw_index) if raw_index is not None else None
        except (TypeError, ValueError):
            index = None
        return STTEvent(
            type="transcript",
            text=text,
            is_final=True,
            segment_index=index,
            utterance_id=str(data.get("utterance_id") or ""),
        )
    if kind == "error":
        err = data.get("error") if isinstance(data.get("error"), dict) else {}
        message = data.get("message") or err.get("message") or "Gnani STT error"
        raise RuntimeError(str(message))
    return None


class STTStream:
    """One Prisma realtime socket. Sends 1,024-byte frames, then waits 64 ms."""

    def __init__(self, language: str, locked: bool = True) -> None:
        self.language = language
        self.locked = locked
        self.lang_code = stt_code(language, locked=locked)
        self.ws = None
        self.connected = False
        self._buffer = bytearray()
        self._closed = False
        self._pump_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self.lang_code = stt_code(self.language, locked=self.locked)
        self.ws = await websockets.connect(
            _ws_base() + "/stt/v3/stream",
            additional_headers=stt_ws_headers(self.lang_code),
            open_timeout=10,
            max_size=None,
        )
        self._pump_task = asyncio.create_task(self._pump())

    async def send_pcm(self, pcm: bytes) -> None:
        if self._closed or not pcm:
            return
        self._buffer.extend(pcm)

    async def _pump(self) -> None:
        try:
            while not self._closed and self.ws is not None:
                if len(self._buffer) < FRAME_BYTES:
                    await asyncio.sleep(0.01)
                    continue
                frame = bytes(self._buffer[:FRAME_BYTES])
                del self._buffer[:FRAME_BYTES]
                await self.ws.send(frame)
                await asyncio.sleep(FRAME_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception:
            return

    async def events(self) -> AsyncIterator[STTEvent]:
        if self.ws is None:
            return
        async for message in self.ws:
            if isinstance(message, bytes):
                continue
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "connected":
                self.connected = True
            event = parse_stt_message(data)
            if event is not None:
                yield event

    async def close(self) -> None:
        self._closed = True
        if self._pump_task and not self._pump_task.done():
            self._pump_task.cancel()
        if self.ws is not None:
            await self.ws.close()
            self.ws = None


async def fetch_tts(text: str, language: str, container: str = "wav", sample_rate: int = 8000) -> bytes:
    """POST /api/v1/tts/inference. The body is audio, not JSON."""
    url = settings.gnani_base_url.rstrip("/") + "/api/v1/tts/inference"
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            url,
            headers={"X-API-Key-ID": settings.gnani_api_key, "Content-Type": "application/json"},
            json=tts_body(text, language, container, sample_rate),
        )
        response.raise_for_status()
        return response.content


async def synthesize_pcm(text: str, language: str) -> tuple[bytes, int]:
    """8 kHz-oriented PCM16. A wav container is stripped; a higher rate is kept for the caller to downsample."""
    raw = await fetch_tts(text, language, "wav", 8000)
    return parse_wav(raw)


async def synthesize(text: str, language: str) -> AsyncIterator[bytes]:
    """Yield 8 kHz PCM16 for the softphone and the phone adapters."""
    pcm, rate = await synthesize_pcm(text, language)
    if rate and rate != 8000:
        pcm = downsample_pcm16(pcm, rate, 8000)
    step = 1600  # 100 ms, so barge-in can cut playback between chunks
    for start in range(0, len(pcm), step):
        yield pcm[start : start + step]


async def synthesize_rest(text: str, language: str, container: str = "wav") -> bytes:
    """Raw Timbre bytes. `mulaw` is headerless G.711; `wav` is a RIFF file."""
    return await fetch_tts(text, language, container)


async def transcribe_rest(audio: bytes, filename: str, language: str, locked: bool = True) -> str:
    """Short clip via POST /stt/v3. Fields are audio_file and language_code only."""
    url = settings.gnani_base_url.rstrip("/") + "/stt/v3"
    files = {"audio_file": (filename or "clip.wav", audio, "audio/wav")}
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            url,
            headers={"X-API-Key-ID": settings.gnani_api_key},
            files=files,
            data=stt_form(language, locked=locked),
        )
        response.raise_for_status()
        body = response.json()
    return str(body.get("transcript") or "").strip()
