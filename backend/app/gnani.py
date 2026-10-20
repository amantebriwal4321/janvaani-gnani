"""Gnani Prisma STT and Timbre TTS. No other speech vendor is called.

REST and WebSocket shapes follow https://docs.gnani.ai (base https://api.vachana.ai,
header X-API-Key-ID). The call path uses 8 kHz PCM so a phone line can reuse it.
"""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator

import httpx
import websockets

from app.audio import take_frames
from app.config import settings
from app.languages import BIAS_WORDS, STT_CODE, TELEPHONY_VAD, TTS_CODE


def _ws_base() -> str:
    base = settings.gnani_base_url.rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base[len("https://") :]
    if base.startswith("http://"):
        return "ws://" + base[len("http://") :]
    return base


def _headers(lang_code: str) -> dict[str, str]:
    headers = {
        "x-api-key-id": settings.gnani_api_key,
        "lang_code": lang_code,
        "x-bias-list": ",".join(BIAS_WORDS),
        **TELEPHONY_VAD,
    }
    return headers


def strip_wav(data: bytes) -> bytes:
    if not data.startswith(b"RIFF") or len(data) < 44:
        return data
    offset = 12
    while offset + 8 <= len(data):
        chunk = data[offset : offset + 4]
        size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        offset += 8
        if chunk == b"data":
            return data[offset : offset + size]
        offset += size
    return data[44:]


class STTStream:
    """One Prisma realtime socket. Frames are 1,024-byte PCM16 chunks at 8 kHz."""

    def __init__(self, language: str) -> None:
        self.language = language
        self.lang_code = STT_CODE.get(language, "hi-IN")
        self.ws = None
        self._buffer = bytearray()
        self._closed = False

    async def connect(self) -> None:
        self.ws, self.lang_code = await _open_stt(self.language)
        if self.lang_code == "hi-IN" and self.language == "hi-en":
            # Socket rejected hi-en. Keep listening in Hindi; dialogue language stays Hinglish.
            pass

    async def send_pcm(self, pcm: bytes) -> None:
        if self.ws is None or self._closed:
            return
        self._buffer.extend(pcm)
        for frame in take_frames(self._buffer):
            await self.ws.send(frame)

    async def transcripts(self) -> AsyncIterator[str]:
        if self.ws is None:
            return
        async for message in self.ws:
            if isinstance(message, bytes):
                continue
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "transcript" and data.get("text"):
                yield str(data["text"]).strip()
            elif data.get("type") == "error":
                raise RuntimeError(data.get("message") or "Gnani STT error")

    async def close(self) -> None:
        self._closed = True
        if self.ws is not None:
            await self.ws.close()
            self.ws = None


async def _open_stt(language: str):
    code = STT_CODE.get(language, "hi-IN")
    ws = await _connect_stt(code)
    try:
        first = await asyncio.wait_for(ws.recv(), timeout=8)
    except TimeoutError:
        return ws, code
    if isinstance(first, str):
        try:
            data = json.loads(first)
        except json.JSONDecodeError:
            data = {}
        message = str(data.get("message") or "")
        if data.get("type") == "error" and code == "hi-en":
            await ws.close()
            ws = await _connect_stt("hi-IN")
            return ws, "hi-IN"
        if data.get("type") == "error":
            await ws.close()
            raise RuntimeError(message or "Gnani STT refused the connection")
    return ws, code


async def _connect_stt(code: str):
    return await websockets.connect(
        _ws_base() + "/stt/v3/stream",
        additional_headers=_headers(code),
        open_timeout=10,
        max_size=None,
    )


def _tts_body(text: str, language: str, container: str = "raw") -> dict:
    return {
        "text": text,
        "voice": settings.gnani_tts_voice,
        "model": settings.gnani_tts_model,
        "language": TTS_CODE.get(language, "hi-IN"),
        "speed": settings.gnani_tts_speed,
        "audio_config": {
            "sample_rate": 8000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": container,
        },
    }


async def synthesize(text: str, language: str) -> AsyncIterator[bytes]:
    """Stream 8 kHz PCM16. Falls back to the REST inference call if the socket fails before audio."""
    url = _ws_base() + "/api/v1/tts"
    try:
        async with websockets.connect(
            url,
            additional_headers={"X-API-Key-ID": settings.gnani_api_key},
            open_timeout=10,
            max_size=None,
        ) as ws:
            await ws.send(json.dumps(_tts_body(text, language, "raw")))
            yielded = False
            async for message in ws:
                if isinstance(message, bytes):
                    yielded = True
                    yield message
                    continue
                data = json.loads(message)
                kind = data.get("type")
                if kind == "audio":
                    payload = (data.get("data") or {}).get("audio") or ""
                    if payload:
                        yielded = True
                        yield base64.b64decode(payload)
                    if (data.get("data") or {}).get("is_final"):
                        break
                elif kind == "complete":
                    break
                elif kind == "error":
                    raise RuntimeError(data.get("message") or "Gnani TTS error")
            if yielded:
                return
    except Exception:
        audio = await synthesize_rest(text, language)
        if audio:
            yield audio
            return
        raise


async def synthesize_rest(text: str, language: str) -> bytes:
    url = settings.gnani_base_url.rstrip("/") + "/api/v1/tts/inference"
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            url,
            headers={"X-API-Key-ID": settings.gnani_api_key, "Content-Type": "application/json"},
            json=_tts_body(text, language, "wav"),
        )
        response.raise_for_status()
        return strip_wav(response.content)


async def transcribe_rest(audio: bytes, filename: str, language: str) -> str:
    """Short clip, at most 60 seconds, via POST /stt/v3."""
    url = settings.gnani_base_url.rstrip("/") + "/stt/v3"
    code = STT_CODE.get(language, "hi-IN")
    files = {"audio_file": (filename or "clip.wav", audio, "application/octet-stream")}
    form = {
        "language_code": code,
        "format": "transcribe",
        "bias_list": ",".join(BIAS_WORDS),
        "bias_score": "1.0",
    }
    async with httpx.AsyncClient(timeout=40) as client:
        response = await client.post(
            url,
            headers={"X-API-Key-ID": settings.gnani_api_key},
            files=files,
            data=form,
        )
        if response.status_code >= 400 and code == "hi-en":
            form["language_code"] = "hi-IN"
            response = await client.post(
                url,
                headers={"X-API-Key-ID": settings.gnani_api_key},
                files=files,
                data=form,
            )
        response.raise_for_status()
        body = response.json()
    return str(body.get("transcript") or "").strip()
