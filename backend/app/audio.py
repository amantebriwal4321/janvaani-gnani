"""PCM16 and G.711 µ-law helpers. The internal call path is 8 kHz mono PCM16."""

from __future__ import annotations

import struct

MULAW_BIAS = 0x84
MULAW_CLIP = 32635
FRAME_BYTES = 1024  # 512 samples, 64 ms at 8 kHz. Prisma's required frame.


def pcm16_rms(pcm: bytes) -> float:
    count = len(pcm) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack("<" + "h" * count, pcm[: count * 2])
    total = 0
    for sample in samples:
        total += sample * sample
    return (total / count) ** 0.5


def downsample_pcm16(pcm: bytes, in_rate: int, out_rate: int = 8000) -> bytes:
    """Integer-ratio downsample. 8 kHz passes through. 16 kHz keeps every other sample."""
    if in_rate == out_rate or in_rate <= 0:
        return pcm
    count = len(pcm) // 2
    if count == 0:
        return b""
    samples = struct.unpack("<" + "h" * count, pcm[: count * 2])
    if in_rate % out_rate == 0:
        step = in_rate // out_rate
        picked = samples[::step]
    else:
        ratio = in_rate / out_rate
        picked = []
        pos = 0.0
        while int(pos) < count:
            picked.append(samples[int(pos)])
            pos += ratio
    if not picked:
        return b""
    return struct.pack("<" + "h" * len(picked), *picked)


def linear_to_ulaw(sample: int) -> int:
    sign = 0x80 if sample < 0 else 0
    if sample < 0:
        sample = -sample
    if sample > MULAW_CLIP:
        sample = MULAW_CLIP
    sample += MULAW_BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and (sample & mask) == 0:
        exponent -= 1
        mask >>= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def ulaw_to_linear(value: int) -> int:
    value = (~value) & 0xFF
    sign = value & 0x80
    exponent = (value >> 4) & 0x07
    mantissa = value & 0x0F
    sample = ((mantissa << 3) + MULAW_BIAS) << exponent
    sample -= MULAW_BIAS
    return -sample if sign else sample


def pcm16_to_mulaw(pcm: bytes) -> bytes:
    count = len(pcm) // 2
    if count == 0:
        return b""
    samples = struct.unpack("<" + "h" * count, pcm[: count * 2])
    return bytes(linear_to_ulaw(sample) for sample in samples)


def mulaw_to_pcm16(payload: bytes) -> bytes:
    if not payload:
        return b""
    samples = [ulaw_to_linear(byte) for byte in payload]
    return struct.pack("<" + "h" * len(samples), *samples)


def take_frames(buffer: bytearray, size: int = FRAME_BYTES) -> list[bytes]:
    frames = []
    while len(buffer) >= size:
        frames.append(bytes(buffer[:size]))
        del buffer[:size]
    return frames
