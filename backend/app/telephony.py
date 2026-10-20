"""Phone-line adapters.

The call session speaks PCM16 at 8 kHz. Each adapter only translates a carrier's
media frames. No account is required: the web softphone is the working path.
Twilio Media Streams use G.711 µ-law. Exotel AgentStream / Voicebot uses 16-bit PCM.
Caller numbers are ignored and never written onto the slip.
"""

from __future__ import annotations

import base64
import json

from app.audio import downsample_pcm16, mulaw_to_pcm16, pcm16_to_mulaw


def twilio_inbound_pcm(message: dict) -> bytes | None:
    if message.get("event") != "media":
        return None
    payload = (message.get("media") or {}).get("payload")
    if not payload:
        return None
    return mulaw_to_pcm16(base64.b64decode(payload))


def exotel_inbound_pcm(message: dict, sample_rate: int = 8000) -> bytes | None:
    if message.get("event") != "media":
        return None
    payload = (message.get("media") or {}).get("payload")
    if not payload:
        return None
    pcm = base64.b64decode(payload)
    rate = sample_rate or 8000
    return downsample_pcm16(pcm, rate, 8000)


def exotel_sample_rate(message: dict) -> int:
    start = message.get("start") or {}
    media = start.get("media_format") or start.get("mediaFormat") or {}
    raw = media.get("sample_rate") or media.get("sampleRate") or 8000
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 8000


class WebTransport:
    name = "web"

    def __init__(self, ws) -> None:
        self.ws = ws

    async def send_json(self, data: dict) -> None:
        await self.ws.send_text(json.dumps(data))

    async def send_pcm(self, pcm: bytes) -> None:
        if pcm:
            await self.ws.send_bytes(pcm)

    async def clear_playback(self) -> None:
        await self.send_json({"type": "clear"})

    async def flush(self) -> None:
        return None


class TwilioTransport:
    """Outbound media is 20 ms µ-law frames. `clear` drops audio still queued at Twilio."""

    name = "twilio"

    def __init__(self, ws) -> None:
        self.ws = ws
        self.sid = ""
        self._mulaw = bytearray()

    async def send_json(self, data: dict) -> None:
        # The browser protocol is not spoken on a Twilio socket. Audio and clear are.
        if data.get("type") == "clear":
            await self.clear_playback()

    async def send_pcm(self, pcm: bytes) -> None:
        self._mulaw.extend(pcm16_to_mulaw(pcm))
        await self._drain(160)

    async def _drain(self, size: int) -> None:
        while len(self._mulaw) >= size:
            chunk = bytes(self._mulaw[:size])
            del self._mulaw[:size]
            await self.ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "streamSid": self.sid,
                        "media": {"payload": base64.b64encode(chunk).decode("ascii")},
                    }
                )
            )

    async def clear_playback(self) -> None:
        self._mulaw.clear()
        await self.ws.send_text(json.dumps({"event": "clear", "streamSid": self.sid}))

    async def flush(self) -> None:
        if not self._mulaw:
            return
        pad = (160 - (len(self._mulaw) % 160)) % 160
        self._mulaw.extend(b"\xff" * pad)
        await self._drain(160)


class ExotelTransport:
    """Outbound PCM must be a multiple of 320 bytes. We send 3,200-byte chunks (200 ms)."""

    name = "exotel"

    def __init__(self, ws) -> None:
        self.ws = ws
        self.sid = ""
        self.sample_rate = 8000
        self._pcm = bytearray()

    async def send_json(self, data: dict) -> None:
        if data.get("type") == "clear":
            await self.clear_playback()

    async def send_pcm(self, pcm: bytes) -> None:
        self._pcm.extend(pcm)
        await self._drain(3200, pad=False)

    async def _drain(self, size: int, pad: bool) -> None:
        if pad and self._pcm:
            extra = (320 - (len(self._pcm) % 320)) % 320
            self._pcm.extend(b"\x00" * extra)
            if len(self._pcm) < size:
                self._pcm.extend(b"\x00" * (size - len(self._pcm)))
        while len(self._pcm) >= size:
            chunk = bytes(self._pcm[:size])
            del self._pcm[:size]
            await self.ws.send_text(
                json.dumps(
                    {
                        "event": "media",
                        "stream_sid": self.sid,
                        "media": {"payload": base64.b64encode(chunk).decode("ascii")},
                    }
                )
            )

    async def clear_playback(self) -> None:
        self._pcm.clear()
        await self.ws.send_text(json.dumps({"event": "clear", "stream_sid": self.sid}))

    async def flush(self) -> None:
        await self._drain(3200, pad=True)
