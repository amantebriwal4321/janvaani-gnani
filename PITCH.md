# JanVaani: a voice desk for welfare forms

**Live:** https://janvaani-gnani.vercel.app · **Code:** https://github.com/amantebriwal4321/janvaani-gnani

Built solo by Aman Tebriwal for Gnani's Great Indian AI Internship Challenge.

## The problem

At a Common Service Centre (CSC) counter, most citizens don't know which scheme they fit. The forms are in English, the operator is busy, and a farmer who lost a crop to rain walks out without applying for PM Fasal Bima. Often the barrier is language and paperwork, not eligibility.

## Who it helps

- Citizens who would rather talk than type, in Hindi, Hinglish, Kannada, Telugu, Tamil, Marathi, Bengali, Malayalam or English.
- CSC operators, who get a filled form and a shortlist instead of starting from zero.

## How it works

1. The caller presses **Start talking** and speaks normally, like at the counter.
2. Gnani Prisma turns speech into text over a live socket.
3. An extractor fills the form: district, state, work, land, crop, age, BPL card, an elder at home. ID numbers are dropped.
4. A deterministic rule engine checks 19 schemes (PM-KISAN, PM Fasal Bima, Ayushman Bharat, Vay Vandana, MGNREGA, e-Shram and more). The language model never decides who qualifies.
5. Gnani Timbre speaks the reply and asks for the next missing field.
6. The desk prints a CSC Ready Slip: a PDF with a QR code, the matched schemes and the documents to carry.

## How Gnani is used

- **Prisma STT** (`gnani-prisma-v2.5`): streaming socket `wss://api.vachana.ai/stt/v3/stream` at 8 kHz, the same rate as a phone line. Locked calls send `hi-IN`, `kn-IN` and so on, auto mode sends `indic-auto`. A bias list of scheme and district names helps with words like "PM-KISAN" and "Kolar". `speech_start` lets the caller barge in.
- **Timbre TTS** (`timbre-v3.0`, voice Shivani): every spoken reply, including the greeting, which is prefetched so the first hello plays fast.
- Measured round trip through our server, median of five runs: **STT about 0.7 s, TTS about 1.3 s**.

No other speech vendor is called.

## Impact

One conversation replaces a form, a scheme lookup and a checklist. The operator gets the right schemes in the citizen's own words, and the citizen leaves with a slip they can bring back. Twilio and Exotel adapters already speak the same call session, so a real phone number is a config change, not a rewrite.

## What's live

- Next.js desk on Vercel, FastAPI voice server on Render.
- Real Prisma and Timbre calls in production, checked on 8 and 9 Nov 2026.
- 19 scheme rules, 65 backend tests, downloadable Ready Slip PDF.
- Practice households only. No real Aadhaar, PAN or phone number is stored.

## Links

- Live desk: https://janvaani-gnani.vercel.app
- Repo: https://github.com/amantebriwal4321/janvaani-gnani
- Voice API health: https://janvaani-api-1eve.onrender.com/api/health
