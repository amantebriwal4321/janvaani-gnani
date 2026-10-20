# JanVaani

A one-stop voice desk for government welfare forms. The caller speaks in Hindi, Hinglish, Kannada, Telugu, Tamil, Marathi, Bengali, Malayalam, or English. JanVaani fills the form, checks schemes with a fixed rule, and prints a CSC Ready Slip.

Speech is **Gnani only**: Prisma for speech-to-text and Timbre for speech. There is no SLNG and no second speech vendor. When `GNANI_API_KEY` is empty, the same call runs in mock mode so the desk can be demoed without a key.

Built for Gnani’s Great Indian AI Internship Challenge (public 60-second demo; deadline 10 November 2026). Practice data only. The app never stores an Aadhaar, PAN, or phone number.

## Run it

From the repo root:

```bash
./dev.sh
```

That starts the API on port 8766 and the desk on port 43123.

- Desk: http://127.0.0.1:43123
- Health: http://127.0.0.1:8766/api/health

`dev.sh` creates a Python virtualenv, installs the API and the desk if needed, and copies `.env.example` to `.env` the first time.

Docker:

```bash
docker compose up --build
```

## The sixty-second demo

1. Open the desk. The badge says **Mock voice** until a Gnani key is set.
2. Tap **Call**. Allow the microphone if the browser asks. In mock mode the mic is for barge-in only; the ears do not transcribe it.
3. Tap **Kolar farmer**. The caption answers in Hindi and names PM-KISAN, Fasal Bima, and Ayushman. The form shows Kolar, farmer, 2 acres, tomato, age 45, crop loss, BPL, and a father aged 72.
4. Tap **Naam alag**, then **Haan**, then **Haan**. Those are the three CSC checks: the name on the ration card does not match, the mobile is linked, a bank account exists.
5. The slip badge turns **Ready for the counter**, with a red **Fix this first** box for the name mismatch. Tap **Download PDF** (English portal text, QR of the share note) or **Copy SMS text**.

Optional second beat, if the video has room: end the call, call again, tap **Mysuru tailor**. The reply is in Kannada and PM Vishwakarma is in the apply list.

## What mock mode does

| Piece | Without a key | With `GNANI_API_KEY` |
| --- | --- | --- |
| Call, rules, slip, PDF, share text | Works | Works |
| Spoken replies | This device’s speech synthesis, labeled mock | Timbre `timbre-v3.0`, voice Shivani, 8 kHz PCM |
| Hearing the caller | Phrase chips and the type box | Prisma streaming STT on the same 8 kHz frames |
| `POST /api/stt` and `POST /api/tts` | 409 | Prisma REST and Timbre |

Eligibility never waits on the key. The rule engine is the decision.

## Architecture

```
Browser softphone (8 kHz PCM16)
        │  WebSocket /ws/call
        ▼
FastAPI CallSession
        ├─ Prisma STT   wss://api.vachana.ai/stt/v3/stream   (skipped in mock)
        ├─ Extractor    rules first, digits and script, no ID numbers
        ├─ LLM gap-fill optional, never overwrites a rule, never decides eligibility
        ├─ Scheme rules 19 schemes
        └─ Timbre TTS   wss://api.vachana.ai/api/v1/tts      (device voice in mock)
```

The browser downsamples the microphone to 8 kHz, 512-sample frames, the same size a phone line would send. Two adapters sit on the same `CallSession`:

- `/ws/telephony/twilio` — G.711 µ-law, 20 ms frames, `clear` on barge-in
- `/ws/telephony/exotel` — 16-bit PCM, 8 kHz by default, 320-byte-aligned media, `clear` on barge-in

Neither adapter needs a paid account to run the desk. A live number is not wired; the web softphone is the demo path. Caller IDs on a start event are discarded.

Language is chosen with the chips, or left on Auto. Auto greets in Hindi and switches from script (Kannada, Telugu, Tamil, Bengali, Malayalam, Devanagari) or from Hinglish markers. Prisma locks language per socket, so a switch reconnects STT. `hi-en` is sent because Timbre and this contest use it; if Prisma rejects it, the socket reconnects as `hi-IN`.

The dialogue model is pluggable and optional. Set `LLM_BASE_URL` to an OpenAI-compatible `/v1` endpoint (self-hosted Evon, or any other chat model). It may only fill empty profile fields. `LLM_ENABLED=off` keeps the extractor alone.

## Schemes

Nineteen schemes, judged in code: PM-KISAN, PM Fasal Bima, Ayushman Bharat, Ayushman Vay Vandana, PM Vishwakarma, PMAY-Gramin, Ujjwala, MGNREGA, IGNOAPS, IGNWPS, disability pension, PMMVY, PM SVANidhi, e-Shram, Jan Dhan, Gruha Lakshmi, Ladki Bahin, Rythu Bharosa, Lakshmir Bhandar. Each verdict is qualify, likely, need one answer, not for you, or not enough facts. The spoken shortlist follows catalog order, not the alphabet.

## Environment

Copy `.env.example` to `.env`.

| Variable | Role |
| --- | --- |
| `GNANI_API_KEY` | Sent as `X-API-Key-ID`. Empty means mock mode. |
| `GNANI_BASE_URL` | Default `https://api.vachana.ai` |
| `GNANI_TTS_MODEL` | `timbre-v3.0` |
| `GNANI_TTS_VOICE` | `Shivani` |
| `GNANI_TTS_SPEED` | `0.92` |
| `LLM_BASE_URL` | OpenAI-compatible base, including `/v1` if the server expects it |
| `LLM_API_KEY` | Bearer token for that endpoint |
| `LLM_MODEL` | Default `evon` |
| `LLM_ENABLED` | `auto` (on when the base URL is set), `on`, or `off` |
| `NEXT_PUBLIC_API_BASE` | Optional. The desk uses `http://<page-host>:8766` when this is empty |

## Tests

```bash
.venv/bin/python -m pytest -q
```

Run from `backend/`, or let pytest use `backend/pytest.ini` (`pythonpath = .` is relative to that directory):

```bash
cd backend && ../.venv/bin/python -m pytest -q
```

The suite covers the Kolar, Mysuru, Nizamabad, and Nagpur households, the rule that an LLM patch cannot overwrite an extracted field, ID-number stripping, echo filtering, µ-law frames, and a full mock WebSocket call through to a PDF.

## What still needs a live key or a phone account

- Hearing a real microphone and hearing Timbre. The client code is complete; it has not been exercised against `api.vachana.ai`.
- Whether Prisma accepts `hi-en` on the stream. The fallback to `hi-IN` is in the client.
- Timbre audio tags such as `<pauses>` between sentences. They are sent; a live voice is the check.
- Evon gap-fill. Point `LLM_BASE_URL` at a self-hosted OpenAI-compatible endpoint.
- A real Exotel or Twilio number. The adapters speak those media protocols; no account is configured.
- Voice cloning. The Timbre endpoint exists; this app does not call it.
- Sessions live in memory on one process. A restart clears slips.

Headphones help. The softphone uses echo cancellation and ignores a long transcript that is only the assistant’s last line, so a short “haan” still counts.
