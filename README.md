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
        │  WebSocket /ws/call
        ▼
FastAPI CallSession          ← one Vercel service, Fluid Compute
        ├─ Prisma STT   wss://api.vachana.ai/stt/v3/stream
        ├─ Extractor    rules first; ID numbers are dropped
        ├─ LLM          optional gap-fill only
        ├─ 19 scheme rules
        └─ Timbre TTS   POST /api/v1/tts/inference
```

On Vercel the Next.js desk and the FastAPI service ship as one project ([Vercel Services](https://vercel.com/docs/services), beta). Public traffic hits one host:

| Path | Service |
| --- | --- |
| `/api/*` | FastAPI (`backend`, entry `main:app`) |
| `/ws/*` | FastAPI, including the voice socket |
| everything else | Next.js (`frontend`) |

`vercel.json` is the deploy config. Leave the Vercel project’s root directory as the repository root. Do not set it to `frontend`.

The voice path stays on FastAPI. Vercel Functions on Fluid Compute accept the WebSocket upgrade and pin that socket to one instance. Next.js does not terminate the call. A call is one connection: audio in, audio out, and the transcript. When the caller asks for the PDF, the browser posts the slip it already shows to `POST /api/slip`, so the file does not depend on the process that held the socket.

Limits, from [Vercel WebSockets](https://vercel.com/docs/functions/websockets) and function duration:

- The socket closes when the function hits its max duration. `vercel.json` asks for 800 seconds. On Hobby the platform cap is 300 seconds and the higher setting is ignored. On Pro the 800 second setting applies. A dropped socket ends the call; start it again.
- There is no affinity between the socket and a later HTTP request. Do not put durable state only in memory. The slip download does not.
- Idle time on the socket is not billed as active CPU. Audio frames and Gnani calls are.

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

`dev.sh` creates a virtualenv, installs dependencies, and copies `.env.example` to `.env` the first time. On a laptop the desk talks to port 8766. On any other host it uses the same origin, which is what the Vercel rewrites expect.

Docker, for a single machine rather than Vercel:

```bash
docker compose up --build
```

## Environment

Copy `.env.example` to `.env`. Never commit `.env`. On Vercel, set the same names in Project Settings → Environment Variables for Production and Preview. Mark `GNANI_API_KEY` and `LLM_API_KEY` as Sensitive. Do not prefix the Gnani key with `NEXT_PUBLIC_`.

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
| `NEXT_PUBLIC_API_BASE` | No | Leave empty on Vercel. Set it only if the API is on another origin. |

Mock mode still completes a call, a scheme match, and a slip. Spoken replies use the device voice, and the microphone is for barge-in only. Phrase chips and the type box supply the words. With a key, the same call uses Prisma and Timbre. `POST /api/stt` and `POST /api/tts` return 409 until the key is set.

## Deploy on Vercel

1. Import this repository into a new Vercel project. The root directory stays `.`.
2. Vercel reads `vercel.json`. Services is in beta on every plan. The framework preset on the dashboard does not replace that file.
3. Add `GNANI_API_KEY` if you want live speech. Leave it unset to deploy a working mock desk.
4. Do not set `NEXT_PUBLIC_API_BASE`.
5. Deploy. Open `/api/health`. `speech` is `mock` or `gnani`, and `schemes` is 19.
6. Open the site, tap Call, and run the demo below.

A call longer than the plan’s function duration ends when Vercel closes the socket. The 60-second demo fits inside the Hobby cap of 300 seconds.

To point a phone number later, set the carrier’s media-stream URL to `wss://<deployment-host>/ws/telephony/twilio` or `.../exotel`. That still needs the carrier account. The browser demo does not.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest -q
```

The suite covers the Kolar, Mysuru, Nizamabad, and Nagpur households, the rule that a model patch cannot overwrite an extracted field, ID-number stripping, the Gnani request shapes, a mock WebSocket call through to a PDF, and a slip posted without a live session.

Live speech, when a key is in the environment:

```bash
cd backend && ../.venv/bin/python scripts/gnani_smoke.py
```

With no key the script prints a skip line and exits 0.

## Sixty-second demo

1. Open the desk. The badge says **Mock voice** until a Gnani key is set.
2. Tap **Call**. Allow the microphone if the browser asks. In mock mode the mic is for barge-in only.
3. Tap **Kolar farmer**. The caption answers in Hindi and names PM-KISAN, Fasal Bima, and Ayushman. The form shows Kolar, farmer, 2 acres, tomato, age 45, crop loss, BPL, and a father aged 72.
4. Tap **Naam alag**, then **Haan**, then **Haan**. Those are the three CSC checks: the names differ, the mobile is linked, a bank account exists.
5. The slip badge turns **Ready for the counter**, with a red **Fix this first** box. Tap **Download PDF** or **Copy SMS text**.

Optional second beat: end the call, call again, tap **Mysuru tailor**. The reply is in Kannada and PM Vishwakarma is in the apply list.

## Not in this repo

- A funded Exotel or Twilio number. The adapters are ready.
- Timbre voice cloning.
- A check that Prisma accepts `indic-auto` on a live socket. The code sends it for Hinglish and auto. The October 2026 live check used `hi-IN`.
- Evon itself. Point `LLM_BASE_URL` at a self-hosted OpenAI-compatible endpoint if you have one.
- Multi-instance memory. Restarting the API, or a new socket after the duration cap, starts a fresh call.

Headphones help. The softphone uses echo cancellation and ignores a long transcript that only repeats the assistant’s last line, so a short “haan” still counts.
