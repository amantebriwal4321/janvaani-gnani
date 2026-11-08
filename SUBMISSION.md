# JanVaani submission text

Paste this into the Gnani form. Deadline 10 Nov 2026, 23:59 IST.

Do not post the drafts below until you approve them. A live LinkedIn or X post is required before the form will accept the entry. This file does not submit anything.

The running site is https://janvaani-gnani.vercel.app. The voice API is https://janvaani-api-1eve.onrender.com. This branch is not deployed. Production still speaks with Gnani. Fixes that are not live yet: Timbre WAV sizes, redacting a Groq organization id on `/api/health`, a lower reasoning budget for gpt-oss, and keeping Ready Slip PDF lines on the page. The PDF from the current server walks each line further right.

## Project title

JanVaani

## Problem

At a Common Service Centre the citizen has to know which welfare scheme fits the household. JanVaani takes a spoken description, fills the form, checks 19 schemes with a fixed rule, and prints a CSC Ready Slip. The voice does not decide eligibility.

## Who uses it

A citizen talking the way they would at the counter, in Hindi, Hinglish, Kannada, Telugu, Tamil, Marathi, Bengali, Malayalam, or English. The demo uses practice households only.

## Gnani models and APIs

- Prisma speech to text, reported by the server as `gnani-prisma-v2.5`. Streaming socket `wss://api.vachana.ai/stt/v3/stream` and REST `POST /stt/v3`. Locked calls send `hi-IN`, `kn-IN`, and the other `-IN` codes. Hinglish and auto send `indic-auto`, because Prisma rejects `hi-en`.
- Timbre text to speech, model `timbre-v3.0`, voice Shivani. `POST /api/v1/tts/inference`. English replies use `en-IN`. Hinglish replies may use `hi-en`.

No other speech vendor is called.

Optional, and not a Gnani model: Groq `openai/gpt-oss-20b` phrases the reply and may fill an empty field. The 19 scheme verdicts stay in code. On 8 Nov 2026 the deployed Groq key returned HTTP 429, tokens per day, so the checked call used the fixed Hindi lines. `llm` on that turn was `fallback`.

## What was checked on 8 Nov 2026

Against the deployed API, not a local mock:

- Health said `speech: gnani`, not `mock`.
- Hindi Timbre audio of "नमस्ते, मैं जनवाणी हूँ।" was speech (8 kHz, not silence). Prisma REST returned "नमस्ते मैं जनवाणी हूँ।" on one pass and "नमस्ते, मैं जनवानी हूँ।" on a later pass.
- Kannada Timbre audio returned "ನಮಸ್ಕಾರ ನಾನು ಜನವಾಣಿ" and, on another clip, "ನಮಸ್ಕಾರ ನಾನು ಜಯವಾಣಿ". One Kannada REST call returned HTTP 500. The next call returned a transcript.
- The call socket opened as `mode: gnani`, `listen: gnani`, Prisma `hi-IN`. The same Hindi audio, sent as PCM, was transcribed as "नमस्ते, मैं जनवाणी हूँ।"
- A typed Kolar line filled Kolar, Karnataka, farmer, 2 acres, tomato, age 45, BPL, elder 72. Rules listed PM-KISAN, PM Fasal Bima, Ayushman Bharat, Ayushman Vay Vandana, old-age pension, and e-Shram. Slip status was `draft`.

No real phone number, Aadhaar, PAN, or recorded citizen call was used. There is no live Exotel or Twilio number.

## Solo contribution

Solo. One person built the browser desk, the FastAPI call socket, the Prisma and Timbre adapters, the 19-scheme rule engine, and the Ready Slip. There is no teammate.

## Draft post

Attach the screen recording of the live desk. Tag Gnani and keep both hashtags. Do not publish until you approve the wording.

### LinkedIn

JanVaani is a voice desk for a CSC counter.

You speak in Hindi, Kannada, or Hinglish. It fills the welfare form, checks 19 schemes with a fixed rule, and prints a Ready Slip. The voice does not decide who qualifies.

Speech is Gnani Prisma (speech to text) and Timbre (text to speech, voice Shivani). Practice households only. No real Aadhaar, phone number, or recorded call.

https://janvaani-gnani.vercel.app

Gnani AI
#GnaniAI #GreatIndianAIInternshipChallenge

Tag the company page https://www.linkedin.com/company/gnani-ai in the composer. Hashtags alone do not tag them.

### X

JanVaani: speak at a CSC counter in Hindi, Kannada, or Hinglish. It fills the form, checks 19 welfare schemes by rule, and prints a Ready Slip.

Prisma STT and Timbre TTS. Practice data only.

https://janvaani-gnani.vercel.app

@GnaniAi
#GnaniAI #GreatIndianAIInternshipChallenge

`@GnaniAi` is the handle linked from Gnani's own LinkedIn post (https://x.com/GnaniAi). Confirm it in the composer before you post.
