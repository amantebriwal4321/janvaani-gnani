"""Language codes for the nine call languages.

Prisma STT, checked live on 2026-10-20, accepts only BCP-47 codes:
as-IN, bn-IN, en-IN, gu-IN, hi-IN, indic-auto, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN.
`hi-en` is rejected. Hinglish and an unlocked auto call use `indic-auto`.
Timbre TTS accepts the same -IN codes, and `hi-en` is valid for Hinglish speech.
"""

LANGS = ("hi", "hi-en", "en", "kn", "te", "ta", "mr", "bn", "ml")

_PRIMARY = {"hi", "en", "kn", "te", "ta", "mr", "bn", "ml"}


def app_language(tag: str | None) -> str | None:
    """Map an STT language tag onto a call language. Unknown tags return None."""
    if not tag:
        return None
    raw = tag.strip().lower().replace("_", "-")
    if raw in {"", "auto", "indic-auto", "unknown", "und"}:
        return None
    if raw in {"hi-en", "hinglish", "hi-latn"}:
        return "hi-en"
    primary = raw.split("-", 1)[0]
    if primary in _PRIMARY:
        return primary
    return None

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

# Letters only, one word each, at most 100. Sent on the Prisma socket as
# x-bias-list with x-bias-score. A digit or symbol drops the whole list.

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
    "Pakur",
    "Bankura",
    "Ranchi",
    "Dhanbad",
    "Bokaro",
    "Dumka",
    "Deoghar",
    "Giridih",
    "Hazaribagh",
    "Jamshedpur",
    "Godda",
    "Sahebganj",
    "Palamu",
    "Gumla",
    "Chaibasa",
    "Jamtara",
    "Ramgarh",
    "Chatra",
    "Koderma",
    "Lohardaga",
    "Simdega",
    "Khunti",
    "Garhwa",
    "Latehar",
    "Jharkhand",
    "Karnataka",
    "Maharashtra",
    "Telangana",
    "Bengal",
    "Kerala",
    "Bihar",
    "Odisha",
    "Assam",
    "Delhi",
    "Punjab",
    "Haryana",
    "Gujarat",
    "Rajasthan",
    "Chhattisgarh",
)
