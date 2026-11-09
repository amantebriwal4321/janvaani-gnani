# JanVaani submission text

Paste this into the Gnani form. Deadline 10 Nov 2026, 23:59 IST.

Do not post the drafts below until you approve them. A live LinkedIn or X post is required before the form will accept the entry. This file does not submit anything.

The running site is https://janvaani-gnani.vercel.app. The voice API is https://janvaani-api-1eve.onrender.com. Pull request 5 was merged to main on 9 Nov 2026 and both deploys finished: Vercel production for that commit is READY, and Render `janvaani-api` reported success. Production now returns a normal WAV size from `/api/tts` and keeps Ready Slip lines on the left of the page.

## Project title

JanVaani

## Problem

At a CSC counter the citizen rarely knows which scheme fits. JanVaani listens, fills the form, checks 19 schemes in code, and prints a Ready Slip. The voice does not decide eligibility.

## Who uses it

A citizen talking the way they would at the counter, in Hindi, Hinglish, Kannada, Telugu, Tamil, Marathi, Bengali, Malayalam, or English. The demo uses practice households only.

## Gnani models and APIs

- Prisma speech to text, reported by the server as `gnani-prisma-v2.5`. Streaming socket `wss://api.vachana.ai/stt/v3/stream` and REST `POST /stt/v3`. Locked calls send `hi-IN`, `kn-IN`, and the other `-IN` codes. Hinglish and auto send `indic-auto`, because Prisma rejects `hi-en`.
- Timbre text to speech, model `timbre-v3.0`, voice Shivani. `POST /api/v1/tts/inference`. English replies use `en-IN`. Hinglish replies may use `hi-en`.

No other speech vendor is called.

Optional, and not a Gnani model: Groq `openai/gpt-oss-20b` may phrase the reply. If it returns HTTP 429, the caller hears the fixed lines and the desk says so. Scheme verdicts stay in code.

The caller's age and an elder's age stay separate. "उम्र पैंतालीस साल" is 45. "पिताजी बहत्तर साल" is an elder at home, 72. Ayushman Vay Vandana then applies to the elder, not the caller. Heard quotes on the PDF use Noto Sans Devanagari and Noto Sans Kannada, so Hindi and Kannada are drawn instead of question marks.

## What was checked on 8 Nov 2026

Against the deployed API, not a local mock:

- Health said `speech: gnani`, not `mock`.
- Hindi Timbre audio of "नमस्ते, मैं जनवाणी हूँ।" was speech (8 kHz, not silence). Prisma REST returned "नमस्ते मैं जनवाणी हूँ।" on one pass and "नमस्ते, मैं जनवानी हूँ।" on a later pass.
- Kannada Timbre audio returned "ನಮಸ್ಕಾರ ನಾನು ಜನವಾಣಿ" and, on another clip, "ನಮಸ್ಕಾರ ನಾನು ಜಯವಾಣಿ". One Kannada REST call returned HTTP 500. The next call returned a transcript.
- The call socket opened as `mode: gnani`, `listen: gnani`, Prisma `hi-IN`. The same Hindi audio, sent as PCM, was transcribed as "नमस्ते, मैं जनवाणी हूँ।"
- A typed Kolar line filled Kolar, Karnataka, farmer, 2 acres, tomato, age 45, BPL, elder 72. Rules listed PM-KISAN, PM Fasal Bima, Ayushman Bharat, Ayushman Vay Vandana, old-age pension, and e-Shram. Slip status was `draft`.

No real phone number, Aadhaar, PAN, or recorded citizen call was used. There is no live Exotel or Twilio number.

## What was checked on 9 Nov 2026, after the deploy

- `GET /api/health` returned `speech: gnani`, Prisma `gnani-prisma-v2.5`, Timbre `timbre-v3.0`, voice Shivani, 19 schemes, and an empty `llm_error`.
- A Hindi Timbre wav was a normal RIFF file. The data size matched the bytes on disk. Python's wave module read 2.24 seconds. It was not the old `0xFFFFFFFF` streaming header.
- `backend/scripts/probe_deployed.py` failed once: Hindi `/api/stt` returned HTTP 500 twice. The same clip, sent again immediately, transcribed as "नमस्ते, मैं जनवाणी हूँ।" A full probe then exited 0. Hindi came back as "नमस्ते, मैं जनवानी हूँ।" Kannada came back as "ನಮಸ್ಕಾರ ನಾನು ಜನವಾಣಿ".
- A production slip PDF (JV-0833) has every text line starting at x 36.85. The lines stay on the page. Devanagari inside a "heard" quote is replaced by question marks because the slip font is Helvetica. The English values and scheme names are readable.
- The speech demo did not use the canned demo button. There is no microphone on this machine. Chrome's fake mic played a Timbre wav of one practice household sentence, and that same wav was played out so the recording has it. Prisma, on the live call socket, transcribed "मैं कोलार के पास एक गाँव से हूँ। दो एकड़ में टमाटर उगाता हूँ। उम्र पैंतालीस साल है। इस बार बारिश से फसल खराब हो गई।" and a following chunk "बी पी एल कार्ड है। पिताजी बहत्तर साल के हैं।" Timbre spoke the reply. The slip was draft JV-0833, with PM-KISAN, PM Fasal Bima, Ayushman Vay Vandana, MGNREGA, and e-Shram. The downloaded PDF was opened from production.

## Solo contribution

Solo. I built the desk, the call socket, the Prisma and Timbre adapters, the 19 scheme rules, and the Ready Slip. No teammate.

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
