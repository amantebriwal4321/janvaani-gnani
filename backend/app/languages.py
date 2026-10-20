"""Language codes for the nine call languages.

Gnani's published STT table (docs.gnani.ai, verified Aug 2026) uses BCP-47:
bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN.
It does not list the short codes from the contest brief (kn, ta, te, …).
TTS accepts those BCP-47 codes plus hi-en for Hinglish.
We send hi-en to Prisma as well, and reconnect with hi-IN if the socket rejects it.
"""

LANGS = ("hi", "hi-en", "en", "kn", "te", "ta", "mr", "bn", "ml")

STT_CODE = {
    "hi": "hi-IN",
    "hi-en": "hi-en",
    "en": "en-IN",
    "kn": "kn-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ml": "ml-IN",
}

TTS_CODE = dict(STT_CODE)

BROWSER_LANG = {
    "hi": "hi-IN",
    "hi-en": "hi-IN",
    "en": "en-IN",
    "kn": "kn-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ml": "ml-IN",
}

# Telephony preset from the Prisma realtime guide: noisy 8 kHz lines.
# min-segment stays at 120 ms so a short "haan" / "yes" still opens a segment.
TELEPHONY_VAD = {
    "x-sample-rate": "8000",
    "x-format": "transcribe",
    "x-vad-threshold": "0.7",
    "x-min-silence-ms": "480",
    "x-min-speech-ms": "200",
    "x-min-segment-ms": "120",
    "x-bias-score": "1.0",
}

# Letters only, one word each. Hyphenated scheme names are split.
BIAS_WORDS = (
    "PMKISAN",
    "Kisan",
    "Ayushman",
    "Vishwakarma",
    "Ujjwala",
    "MGNREGA",
    "SVANidhi",
    "eShram",
    "JanDhan",
    "Gruha",
    "Lakshmi",
    "Ladki",
    "Bahin",
    "Rythu",
    "Bharosa",
    "Lakshmir",
    "Bhandar",
    "Fasal",
    "Bima",
    "Matru",
    "Vandana",
    "Aadhaar",
    "PMAY",
    "NSAP",
    "Antyodaya",
    "Kolar",
    "Mysuru",
    "Nagpur",
    "Nizamabad",
)
