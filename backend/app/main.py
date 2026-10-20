"""JanVaani API. Speech is Gnani when GNANI_API_KEY is set. Scheme decisions are never the LLM's."""

from __future__ import annotations

import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.config import settings
from app.languages import BIAS_WORDS
from app.schemes import CATALOG
from app.session import SESSIONS, CallSession
from app.slip import build_pdf, render_pdf, slip_from_client
from app.telephony import ExotelTransport, TwilioTransport, WebTransport, exotel_inbound_pcm, exotel_sample_rate, twilio_inbound_pcm

app = FastAPI(title="JanVaani", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "speech": "gnani" if settings.gnani_on else "mock",
        "stt": "gnani-prisma-v2.5",
        "tts": settings.gnani_tts_model,
        "voice": settings.gnani_tts_voice,
        "llm": settings.llm_model if settings.llm_on else "off",
        "sample_rate": settings.sample_rate,
        "schemes": len(CATALOG),
        "bias_words": len(BIAS_WORDS),
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, "That call has ended, or it never started on this server.")
    return session.brain.snapshot()


@app.get("/api/sessions/{session_id}/slip.pdf")
def slip_pdf(session_id: str) -> Response:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, "No slip for that call.")
    pdf = build_pdf(session.brain)
    filename = f"{session.brain.ref}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/slip")
async def slip_download(body: dict) -> Response:
    """PDF from the snapshot the browser already shows. No session lookup."""
    if not isinstance(body, dict):
        raise HTTPException(400, "Expected the slip from this call.")
    snap = slip_from_client(body)
    pdf = render_pdf(snap)
    filename = f"{snap['ref']}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/sessions/{session_id}/share.txt")
def share(session_id: str) -> Response:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(404, "No summary for that call.")
    return Response(content=session.brain.snapshot()["share_text"], media_type="text/plain; charset=utf-8")


@app.post("/api/stt")
async def stt_clip(file: UploadFile = File(...), language: str = Form("hi")) -> dict:
    """Short clip (60 seconds or less) through Prisma REST. Mock mode does not invent a transcript."""
    if not settings.gnani_on:
        raise HTTPException(409, "GNANI_API_KEY is not set. The call page can still run in mock mode.")
    from app.gnani import transcribe_rest

    audio = await file.read()
    if not audio:
        raise HTTPException(400, "Empty audio.")
    transcript = await transcribe_rest(audio, file.filename or "clip.wav", language)
    return {"transcript": transcript, "language": language}


@app.post("/api/tts")
async def tts_clip(body: dict) -> Response:
    if not settings.gnani_on:
        raise HTTPException(409, "GNANI_API_KEY is not set. Mock calls use the device voice.")
    from app.gnani import synthesize_rest

    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "Missing text.")
    container = str(body.get("container") or "wav")
    if container not in ("wav", "mulaw", "raw"):
        container = "wav"
    audio = await synthesize_rest(text, str(body.get("language") or "hi"), container)
    if container == "mulaw":
        media = "audio/basic"
    elif container == "raw":
        media = "application/octet-stream"
    else:
        media = "audio/wav"
    return Response(content=audio, media_type=media)


@app.websocket("/ws/call")
async def ws_call(ws: WebSocket) -> None:
    await ws.accept()
    transport = WebTransport(ws)
    session = CallSession(transport)
    try:
        while True:
            incoming = await ws.receive()
            if incoming["type"] == "websocket.disconnect":
                break
            if incoming.get("text"):
                data = json.loads(incoming["text"])
                kind = data.get("type")
                if kind == "start":
                    await session.start(data.get("language") or "auto")
                elif kind == "utterance":
                    await session.on_text(data.get("text") or "", "text")
                elif kind == "barge_in":
                    await session.barge()
                elif kind == "set_language":
                    session.brain.set_language(data.get("language") or "auto")
                    await transport.send_json({"type": "state", "state": session.brain.snapshot()})
                elif kind == "speak_done":
                    await session.on_speak_done(data.get("turnId"))
            elif incoming.get("bytes"):
                await session.on_pcm(incoming["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()


@app.websocket("/ws/telephony/twilio")
async def ws_twilio(ws: WebSocket) -> None:
    """Twilio Media Streams. Point a number here later. Caller id is discarded."""
    await ws.accept()
    transport = TwilioTransport(ws)
    session = CallSession(transport)
    try:
        while True:
            data = json.loads(await ws.receive_text())
            event = data.get("event")
            if event == "start":
                start = data.get("start") or {}
                transport.sid = start.get("streamSid") or data.get("streamSid") or ""
                await session.start("auto")
            elif event == "media":
                pcm = twilio_inbound_pcm(data)
                if pcm:
                    await session.on_pcm(pcm)
            elif event == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()


@app.websocket("/ws/telephony/exotel")
async def ws_exotel(ws: WebSocket) -> None:
    """Exotel Voicebot / AgentStream. Audio is 8 kHz PCM16 unless the start event says otherwise."""
    await ws.accept()
    transport = ExotelTransport(ws)
    session = CallSession(transport)
    try:
        while True:
            data = json.loads(await ws.receive_text())
            event = data.get("event")
            if event == "start":
                start = data.get("start") or {}
                transport.sid = data.get("stream_sid") or start.get("stream_sid") or ""
                transport.sample_rate = exotel_sample_rate(data)
                await session.start("auto")
            elif event == "media":
                pcm = exotel_inbound_pcm(data, transport.sample_rate)
                if pcm:
                    await session.on_pcm(pcm)
            elif event == "stop":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await session.close()
