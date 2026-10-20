# JanVaani

A voice desk for government welfare forms. The caller speaks in Hindi, Hinglish, Kannada, Telugu, Tamil, Marathi, Bengali, Malayalam, or English. JanVaani fills the form, checks schemes with a fixed rule, and prints a CSC Ready Slip.

Speech is Gnani only: [Prisma](https://docs.gnani.ai) for speech-to-text and Timbre for speech. There is no second speech vendor. When `GNANI_API_KEY` is empty, the same call runs in mock mode.

Built for Gnani’s Great Indian AI Internship Challenge. Practice data only. The app never stores an Aadhaar, PAN, or phone number.

## Features

- A browser softphone at 8 kHz, the same rate a phone line uses. Barge-in is supported. No paid telephony account is required for the demo.
- Auto language detection, or a one-tap language pick. Hinglish is a first-class dialogue language.
- Nineteen welfare schemes, decided by a deterministic rule engine. The language model never decides eligibility.
- Conversational form filling, a document checklist, and nearest-CSC guidance.
- A printable CSC Ready Slip (PDF, with a QR code) and an SMS-style note the caller can copy.
- Provider adapters for a later Exotel or Twilio number. They speak the same call session as the browser.

## Schemes

PM-KISAN, PM Fasal Bima, Ayushman Bharat, Ayushman Vay Vandana, PM Vishwakarma, PMAY-Gramin, Ujjwala, MGNREGA, IGNOAPS, IGNWPS, disability pension, PMMVY, PM SVANidhi, e-Shram, Jan Dhan, Gruha Lakshmi, Ladki Bahin, Rythu Bharosa, and Lakshmir Bhandar.

Each verdict is qualify, likely, need one answer, not for you, or not enough facts. The spoken shortlist follows catalog order.

## Architecture

```
Browser (8 kHz PCM16)
        │  wss://<render-host>/ws/call
        ▼
FastAPI on Render            ← WebSocket stays open for the call
        ├─ Prisma STT   wss://api.vachana.ai/stt/v3/stream
        ├─ Extractor    rules first; ID numbers are dropped
        ├─ LLM          optional gap-fill only
        ├─ 19 scheme rules
        └─ Timbre TTS   POST /api/v1/tts/inference
                ▲
Next.js on Vercel  ─────────┘  NEXT_PUBLIC_API_BASE / NEXT_PUBLIC_WS_BASE
```

Vercel serves the desk. It does not hold the call socket: a function dies while the citizen is still talking, and the line drops. The FastAPI process on Render accepts `/ws/call` and keeps that one connection up. Audio in, audio out, and the transcript share it.

The slip does not need that process. When the caller downloads the PDF, the browser posts the slip it already shows to `POST /api/slip`.

If `NEXT_PUBLIC_API_BASE` and `NEXT_PUBLIC_WS_BASE` are empty, the desk uses the same origin. On a laptop that is port 8766. On any other host it is the page’s own origin, which is what a single-machine Docker deploy expects.

Phone adapters, unused until a carrier is pointed at them:

- `wss://<your-host>/ws/telephony/twilio` — G.711 µ-law, 20 ms frames, `clear` on barge-in
- `wss://<your-host>/ws/telephony/exotel` — 16-bit PCM, 8 kHz by default, 320-byte aligned

Caller numbers on a start event are discarded.

### Gnani

Prisma STT accepts BCP-47 codes only (`hi-IN`, `kn-IN`, and the rest of the `-IN` set). It rejects `hi-en`. Hinglish and an unlocked auto call send `indic-auto`. A locked language uses its `-IN` code, and the socket reconnects when that code changes. Timbre may still be asked for `hi-en` when the reply itself is Hinglish.

The realtime socket sends `x-api-key-id`, `lang_code`, `x-sample-rate: 8000`, and `x-min-silence-ms: 400`. Audio goes up as 1,024-byte frames, one every 64 ms. `speech_start` interrupts playback. A final `transcript` is the caller’s turn.

Timbre’s REST body is `voice`, `model`, `language`, and `audio_config`. The response is the audio itself. `container: mulaw` is raw 8 kHz G.711.

The dialogue model is optional. Set `LLM_BASE_URL` to an OpenAI-compatible endpoint (self-hosted Evon, or any other chat model). It may only fill empty profile fields.

## Run locally

```bash
./dev.sh
```

- Desk: http://127.0.0.1:43123
- Health: http://127.0.0.1:8766/api/health

`dev.sh` creates a virtualenv, installs dependencies, and copies `.env.example` to `.env` the first time. On a laptop the desk talks to port 8766. On any other host, with the public bases empty, it uses the same origin.

Docker, for a single machine rather than Vercel:

```bash
docker compose up --build
```

## Environment

Copy `.env.example` to `.env`. Never commit `.env`. Put `GNANI_API_KEY` and `LLM_API_KEY` on Render only, marked secret. Do not prefix the Gnani key with `NEXT_PUBLIC_`. On Vercel, set only the two `NEXT_PUBLIC_` bases, then redeploy.

| Variable | Required | Role |
| --- | --- | --- |
| `GNANI_API_KEY` | For live speech | Sent as `X-API-Key-ID`. Empty means mock mode. |
| `GNANI_BASE_URL` | No | Default `https://api.vachana.ai` |
| `GNANI_TTS_MODEL` | No | `timbre-v3.0` |
| `GNANI_TTS_VOICE` | No | `Shivani` |
| `GNANI_TTS_SPEED` | No | Stored only. The verified Timbre body does not send speed. |
| `LLM_BASE_URL` | No | OpenAI-compatible base. Empty keeps the extractor alone. |
| `LLM_API_KEY` | No | Bearer token for that endpoint |
| `LLM_MODEL` | No | Default `evon` |
| `LLM_ENABLED` | No | `auto`, `on`, or `off` |
| `NEXT_PUBLIC_API_BASE` | On Vercel | HTTPS origin of the Render API, no trailing slash. Empty means same-origin. Inlined at build time. |
| `NEXT_PUBLIC_WS_BASE` | On Vercel | WebSocket origin, for example `wss://janvaani-api.onrender.com`. Empty derives `ws`/`wss` from the API base, then same-origin. Inlined at build time. |

Mock mode still completes a call, a scheme match, and a slip. Spoken replies use the device voice, and the microphone is for barge-in only. Phrase chips and the type box supply the words. With a key, the same call uses Prisma and Timbre. `POST /api/stt` and `POST /api/tts` return 409 until the key is set.

## Deploy

The desk and the voice server ship separately. Pushes to `main` deploy the Next.js frontend on Vercel. The call socket is the Render service below. Do not point the Vercel project at `frontend` as the root if `vercel.json` is in use: that file already builds the `web` service from `frontend`.

### 1. Render (FastAPI, WebSockets)

`render.yaml` is a Blueprint for one public web service.

1. In the Render dashboard, choose **New → Blueprint** and connect this repository. Render reads `render.yaml`.
2. When it asks for secret env vars, set `GNANI_API_KEY` to the Gnani key. Leave it empty to run the whole call in mock mode. Do not commit the key.
3. Leave `LLM_BASE_URL` and `LLM_API_KEY` empty unless you have an OpenAI-compatible endpoint. Eligibility does not use them.
4. Apply the blueprint. The service builds from `backend/` with `pip install -r requirements.txt` and starts `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Open `https://<your-service>.onrender.com/api/health`. `ok` is true, `schemes` is 19, and `speech` is `mock` or `gnani`.

Docker instead of the Blueprint: **New → Web Service**, environment **Docker**, root directory `backend`, Dockerfile `backend/Dockerfile`. Set the same env vars. Render injects `PORT`.

The free instance sleeps after idle time. The first request wakes it, which can take about a minute; a call needs the service awake. WebSockets are supported on this web service. Do not run the API as a background worker.

### 2. Vercel (Next.js desk)

1. Import this repository. The project root stays the repository root so `vercel.json` is picked up.
2. In **Project Settings → Environment Variables**, for Production and Preview, set:
   - `NEXT_PUBLIC_API_BASE` = `https://<your-service>.onrender.com`
   - `NEXT_PUBLIC_WS_BASE` = `wss://<your-service>.onrender.com`
3. Do not set `GNANI_API_KEY` on Vercel. The key lives only on Render. Never prefix it with `NEXT_PUBLIC_`.
4. Redeploy. Next inlines `NEXT_PUBLIC_*` at build time, so a value added after the build does nothing until the next deploy.
5. Open the site. The first screen says what JanVaani does. **Start talking** opens the line. **Play 60-second demo** runs the scripted Kolar household with the microphone off.

Same-origin fallback: if both public variables are empty, the browser calls the page’s own host (`/api` and `/ws`). Use that for the local `./dev.sh` desk and for `docker compose`. A Vercel deploy with both empty cannot reach Render.

To point a phone number later, set the carrier’s media-stream URL to `wss://<render-host>/ws/telephony/twilio` or `.../exotel`. That still needs the carrier account. The browser demo does not.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest -q
```

The suite covers the Kolar, Mysuru, Nizamabad, and Nagpur households, the rule that a model patch cannot overwrite an extracted field, ID-number stripping, the Gnani request shapes, a mock WebSocket call through to a PDF, a slip posted without a live session, the scripted demo household, filler acknowledgements, and sentence-sized speech.

Live speech, when a key is in the environment:

```bash
cd backend && ../.venv/bin/python scripts/gnani_smoke.py
```

With no key the script prints a skip line and exits 0.

## Sixty-second demo

1. Open the desk. The first screen says what the call does. **Powered by Gnani.ai** sits under the button. The voice badge says **Practice voice** until a Gnani key is set.
2. Tap **Play 60-second demo**. The microphone stays off. A scripted Kolar household speaks the lines below, with a short pause after each reply.
3. Or tap **Start talking**, allow the microphone, and tap **Kolar farmer**. In mock mode the mic is for barge-in only.
4. The caption answers in Hindi and names PM-KISAN, Fasal Bima, and Ayushman. The form fills in: Kolar, farmer, 2 acres, tomato, age 45, crop loss, BPL, and a father aged 72.
5. Tap **Naam alag**, then **Haan**, then **Haan**. Those are the three CSC checks: the names differ, the mobile is linked, a bank account exists.
6. The slip turns **Ready for the counter**, with a red **Fix this first** box. Tap **Download PDF** or **Copy SMS text**.

Optional second beat: end the call, call again, tap **Mysuru tailor**. The reply is in Kannada and PM Vishwakarma is in the apply list.

## Not in this repo

- A funded Exotel or Twilio number. The adapters are ready.
- Timbre voice cloning.
- A check that Prisma accepts `indic-auto` on a live socket. The code sends it for Hinglish and auto. The October 2026 live check used `hi-IN`.
- Evon itself. Point `LLM_BASE_URL` at a self-hosted OpenAI-compatible endpoint if you have one.
- Multi-instance memory. Restarting the API, or a new socket after the duration cap, starts a fresh call.

Headphones help. The softphone uses echo cancellation and ignores a long transcript that only repeats the assistant’s last line, so a short “haan” still counts.
