#!/usr/bin/env python3
"""Tell a deployed JanVaani apart from mock mode.

Calls the public desk API only. Does not read GNANI_API_KEY and does not print
provider error bodies (those can contain an account id).

    cd backend && ../.venv/bin/python scripts/probe_deployed.py
    JANVAANI_API_BASE=https://janvaani-api-1eve.onrender.com ../.venv/bin/python scripts/probe_deployed.py

Exit 0: Prisma transcribed a Timbre clip in Hindi and in Kannada.
Exit 3: the server is in mock mode, or /api/tts returns 409.
Exit 1: the server claims Gnani, but the audio is silent or the transcript is empty.
"""

from __future__ import annotations

import io
import math
import os
import re
import struct
import sys
import wave

import httpx

DEFAULT_BASE = "https://janvaani-api-1eve.onrender.com"
# The greeting word is stable. Prisma has spelled the name JanVaani more than one way
# (जनवाणी / जनवानी, ಜನವಾಣಿ / ಜಯವಾಣಿ), so the name is not the pass condition.
CLIPS = (
    ("hi", "नमस्ते, मैं जनवाणी हूँ।", "नमस्ते"),
    ("kn", "ನಮಸ್ಕಾರ, ನಾನು ಜನವಾಣಿ.", "ನಮಸ್ಕಾರ"),
)


def _base() -> str:
    return (os.environ.get("JANVAANI_API_BASE") or DEFAULT_BASE).rstrip("/")


def _pcm_from_wav(data: bytes) -> tuple[bytes, int]:
    """PCM and sample rate. Timbre sets chunk sizes to 0xFFFFFFFF, which wave misreads."""
    if len(data) < 44 or not data.startswith(b"RIFF"):
        return b"", 8000
    rate = int.from_bytes(data[24:28], "little") or 8000
    if rate > 96000:
        rate = 8000
    if data[36:40] == b"data":
        declared = int.from_bytes(data[40:44], "little")
        if declared > len(data) - 44:
            return data[44:], rate
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            return handle.readframes(handle.getnframes()), handle.getframerate() or rate
    except wave.Error:
        return data[44:], rate


def _wav_rms(data: bytes) -> tuple[float, float]:
    pcm, rate = _pcm_from_wav(data)
    if len(pcm) < 2:
        return 0.0, 0.0
    count = len(pcm) // 2
    samples = struct.unpack("<" + "h" * count, pcm[: count * 2])
    rms = math.sqrt(sum(sample * sample for sample in samples) / count)
    seconds = count / float(rate)
    return rms, seconds


def _llm_status(error: str) -> str:
    if not error:
        return "empty"
    match = re.search(r"HTTP\s+(\d{3})", error)
    if match:
        return f"HTTP {match.group(1)}"
    return "set"


def main() -> int:
    base = _base()
    print(f"base {base}")
    with httpx.Client(timeout=60) as client:
        health = client.get(base + "/api/health")
        print(f"health HTTP {health.status_code}")
        if health.status_code != 200:
            print(health.text[:180])
            return 1
        body = health.json()
        speech = body.get("speech")
        print(
            "speech={speech} stt={stt} tts={tts} voice={voice} schemes={schemes} llm={llm} llm_error={err}".format(
                speech=speech,
                stt=body.get("stt"),
                tts=body.get("tts"),
                voice=body.get("voice"),
                schemes=body.get("schemes"),
                llm=body.get("llm"),
                err=_llm_status(str(body.get("llm_error") or "")),
            )
        )
        if speech != "gnani":
            tts = client.post(base + "/api/tts", json={"text": "नमस्ते", "language": "hi"})
            print(f"mock check /api/tts HTTP {tts.status_code}")
            print("This server is not running Gnani speech. No transcript is claimed.")
            return 3

        for language, text, needle in CLIPS:
            tts = client.post(
                base + "/api/tts",
                json={"text": text, "language": language, "container": "wav"},
            )
            rms, seconds = _wav_rms(tts.content)
            print(
                f"tts {language} HTTP {tts.status_code} bytes={len(tts.content)} "
                f"rms={rms:.0f} seconds={seconds:.2f}"
            )
            if tts.status_code != 200 or rms < 400:
                print(f"{language} audio is missing or silent. Not counting this as Gnani speech.")
                return 1
            stt = None
            for attempt in (1, 2):
                stt = client.post(
                    base + "/api/stt",
                    files={"file": (f"{language}.wav", tts.content, "audio/wav")},
                    data={"language": language},
                )
                if stt.status_code < 500:
                    break
                print(f"stt {language} HTTP {stt.status_code} on attempt {attempt}")
            transcript = ""
            if stt is not None and stt.status_code == 200:
                transcript = str(stt.json().get("transcript") or "")
            print(f"stt {language} HTTP {stt.status_code if stt else 0} transcript={transcript!r}")
            if stt is None or stt.status_code != 200 or needle not in transcript:
                print(f"{language} transcript did not match the clip. Not counting this as Gnani success.")
                return 1
    print("probe ok: Timbre audio was transcribed by Prisma in Hindi and Kannada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
