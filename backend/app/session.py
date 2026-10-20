"""One call, whether it arrives from the browser softphone or a phone-line adapter."""

from __future__ import annotations

import asyncio

from app.audio import pcm16_rms
from app.config import settings
from app.dialogue import strip_tags
from app.engine import Brain, echo_of_assistant
from app.gnani import STTEvent, STTStream, stt_code, synthesize
from app.languages import BROWSER_LANG
from app.llm import LLMClient

SESSIONS: dict[str, "CallSession"] = {}


class CallSession:
    def __init__(self, transport) -> None:
        self.transport = transport
        self.brain = Brain()
        self.generation = 0
        self.speaking = False
        self.speak_task: asyncio.Task | None = None
        self.turn_lock = asyncio.Lock()
        self.started = False
        self.closed = False
        self.hot_frames = 0
        self._stt_task: asyncio.Task | None = None
        self._stt: STTStream | None = None
        SESSIONS[self.brain.session_id] = self

    async def start(self, language: str) -> None:
        if self.started:
            return
        self.started = True
        self.brain.set_language(language or "auto")
        if settings.gnani_on:
            self._stt_task = asyncio.create_task(self._listen())
        result = self.brain.greet()
        await self.transport.send_json(
            {
                "type": "ready",
                "sessionId": self.brain.session_id,
                "ref": self.brain.ref,
                "mode": "gnani" if settings.gnani_on else "mock",
                "language": self.brain.language,
                "sampleRate": 8000,
            }
        )
        await self._publish(result, user_text=None)

    async def on_text(self, text: str, source: str) -> None:
        text = (text or "").strip()
        if not text or self.closed:
            return
        if source == "stt" and echo_of_assistant(text, self.brain.last_reply):
            return
        async with self.turn_lock:
            await self.barge()
            llm = LLMClient() if settings.llm_on else None
            result = await self.brain.utterance(text, llm)
            await self._publish(result, user_text=text, source=source)

    async def on_stt_event(self, event: STTEvent) -> None:
        if event.type == "speech_start":
            await self.barge()
            return
        if event.type == "transcript" and event.is_final and event.text:
            await self.on_text(event.text, "stt")

    async def on_pcm(self, pcm: bytes) -> None:
        if self.closed or not pcm:
            return
        if self._stt is not None:
            try:
                await self._stt.send_pcm(pcm)
            except Exception:
                pass
        # The browser decides its own barge-in. A phone line has no client VAD,
        # so sustained inbound energy while we are talking clears playback.
        if self.transport.name != "web" and self.speaking and pcm16_rms(pcm) > 1400:
            self.hot_frames += 1
            if self.hot_frames >= 4:
                self.hot_frames = 0
                await self.barge()
        else:
            self.hot_frames = 0

    async def on_speak_done(self, turn_id) -> None:
        if turn_id == self.generation:
            self.speaking = False
            await self.transport.send_json({"type": "status", "phase": "listening"})

    async def barge(self) -> None:
        was = self.speaking or (self.speak_task is not None and not self.speak_task.done())
        self.generation += 1
        self.speaking = False
        if self.speak_task and not self.speak_task.done():
            self.speak_task.cancel()
        if was:
            await self.transport.clear_playback()
            await self.transport.send_json({"type": "status", "phase": "listening", "barged": True})

    async def close(self) -> None:
        self.closed = True
        self.generation += 1
        if self.speak_task and not self.speak_task.done():
            self.speak_task.cancel()
        if self._stt_task and not self._stt_task.done():
            self._stt_task.cancel()
        if self._stt is not None:
            await self._stt.close()

    async def _publish(self, result, user_text: str | None, source: str = "text") -> None:
        if user_text:
            await self.transport.send_json(
                {"type": "transcript", "role": "user", "text": user_text, "source": source}
            )
        await self.transport.send_json({"type": "state", "state": result.snapshot})
        await self.transport.send_json(
            {
                "type": "transcript",
                "role": "assistant",
                "text": result.reply,
                "language": result.language,
            }
        )
        gen = self.generation
        self.speak_task = asyncio.create_task(self._speak(result.tts, gen))

    async def _speak(self, text: str, generation: int) -> None:
        self.speaking = True
        try:
            await self.transport.send_json({"type": "status", "phase": "speaking", "turnId": generation})
            if not settings.gnani_on:
                await self.transport.send_json(
                    {
                        "type": "speak",
                        "text": text,
                        "language": self.brain.language,
                        "audio": "browser",
                        "turnId": generation,
                        "browserLang": BROWSER_LANG.get(self.brain.language, "hi-IN"),
                    }
                )
                return
            await self.transport.send_json(
                {
                    "type": "audio_start",
                    "sampleRate": 8000,
                    "encoding": "pcm_s16le",
                    "turnId": generation,
                }
            )
            try:
                async for chunk in synthesize(text, self.brain.language):
                    if generation != self.generation or self.closed:
                        return
                    await self.transport.send_pcm(chunk)
            except Exception as exc:
                if generation != self.generation or self.closed:
                    return
                await self.transport.send_json(
                    {
                        "type": "speak",
                        "text": strip_tags(text),
                        "language": self.brain.language,
                        "audio": "browser",
                        "fallback": True,
                        "turnId": generation,
                        "browserLang": BROWSER_LANG.get(self.brain.language, "hi-IN"),
                        "detail": str(exc)[:180],
                    }
                )
                return
            if generation == self.generation and not self.closed:
                flush = getattr(self.transport, "flush", None)
                if flush:
                    await flush()
                await self.transport.send_json({"type": "audio_end", "turnId": generation})
        except asyncio.CancelledError:
            return

    async def _listen(self) -> None:
        while not self.closed:
            stream = STTStream(self.brain.language, locked=self.brain.language_locked)
            self._stt = stream
            try:
                await stream.connect()
                await self.transport.send_json(
                    {"type": "stt", "ready": True, "lang": stream.lang_code, "sampleRate": 8000}
                )
                async for event in stream.events():
                    await self.on_stt_event(event)
                    code = stt_code(self.brain.language, locked=self.brain.language_locked)
                    if code != stream.lang_code or self.closed:
                        break
            except asyncio.CancelledError:
                await stream.close()
                raise
            except Exception as exc:
                await self.transport.send_json({"type": "error", "message": f"Gnani STT: {str(exc)[:180]}"})
                await asyncio.sleep(1)
            finally:
                await stream.close()
                if self._stt is stream:
                    self._stt = None
