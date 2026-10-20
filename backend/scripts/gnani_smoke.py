#!/usr/bin/env python3
"""Live Prisma + Timbre smoke test.

Reads GNANI_API_KEY from the environment (or the repo .env via app settings).
Exits 0 without calling the API when the key is absent. Does not print the key.

    cd backend && ../.venv/bin/python scripts/gnani_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.gnani import STTStream, fetch_tts, parse_wav, transcribe_rest  # noqa: E402


async def _run() -> None:
    print("TTS hi-IN wav…")
    wav = await fetch_tts("नमस्ते, मैं जनवाणी हूँ।", "hi", "wav", 8000)
    if wav[:1] == b"{":
        raise SystemExit(f"TTS returned JSON, not audio: {wav[:180]!r}")
    pcm, rate = parse_wav(wav)
    print(f"  {len(wav)} bytes, pcm {len(pcm)} at {rate} Hz")

    print("TTS mulaw container…")
    mulaw = await fetch_tts("नमस्ते", "hi", "mulaw")
    if mulaw.startswith(b"RIFF") or mulaw[:1] == b"{":
        raise SystemExit("mulaw response was not raw G.711")
    print(f"  {len(mulaw)} raw bytes")

    print("STT REST language_code=hi-IN…")
    transcript = await transcribe_rest(wav, "smoke.wav", "hi", locked=True)
    print(f"  {transcript!r}")
    if not transcript:
        raise SystemExit("REST STT returned an empty transcript")

    print("STT websocket lang_code=hi-IN, 1024-byte frames…")
    if rate != 8000:
        from app.audio import downsample_pcm16

        pcm = downsample_pcm16(pcm, rate, 8000)
    pcm += b"\x00\x00" * 8000 * 2
    stream = STTStream("hi", locked=True)
    await stream.connect()
    if stream.lang_code != "hi-IN":
        raise SystemExit(f"socket language was {stream.lang_code}")
    await stream.send_pcm(pcm)
    heard: list[str] = []

    async def watch() -> None:
        async for event in stream.events():
            print(f"  {event.type} {event.text!r} segment={event.segment_index}")
            if event.type == "transcript" and event.text:
                heard.append(event.text)

    try:
        await asyncio.wait_for(watch(), timeout=18)
    except TimeoutError:
        pass
    finally:
        await stream.close()
    text = " ".join(heard)
    if not stream.connected:
        raise SystemExit("websocket never sent connected")
    print(f"  ws transcript: {text!r}")
    if not text:
        raise SystemExit("websocket returned no final transcript")
    print("smoke ok")


def main() -> int:
    if not settings.gnani_on:
        print("GNANI_API_KEY is not set. Live smoke test skipped.")
        return 0
    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
