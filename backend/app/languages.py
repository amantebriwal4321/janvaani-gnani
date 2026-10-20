"""Language codes for the nine call languages.

Prisma STT, checked live on 2026-10-20, accepts only BCP-47 codes:
as-IN, bn-IN, en-IN, gu-IN, hi-IN, indic-auto, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN.
`hi-en` is rejected. Hinglish and an unlocked auto call use `indic-auto`.
Timbre TTS accepts the same -IN codes, and `hi-en` is valid for Hinglish speech.
"""

LANGS = ("hi", "hi-en", "en", "kn", "te", "ta", "mr", "bn", "ml")

# Prisma language_code / lang_code. Never hi-en.
STT_CODE = {
    "hi": "hi-IN",
    "en": "en-IN",
    "kn": "kn-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ml": "ml-IN",
}

TTS_CODE = {
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

# Letters only, one word each. Kept for the desk; the live Prisma socket
# that transcribed 8 kHz audio did not require a bias header.

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
