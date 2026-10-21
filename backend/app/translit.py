"""Latin letters for Devanagari and Bengali place names. No extra packages.

Used to fuzzy-match a mangled district. It is not a general translator.
"""

from __future__ import annotations

import re

# Consonant, then an optional nukta, then a matra or virama.
_DEV_CONS = {
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "ng",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "ny",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
}
_DEV_NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "न": "n"}
_DEV_VOWEL = {
    "अ": "a",
    "आ": "a",
    "इ": "i",
    "ई": "i",
    "उ": "u",
    "ऊ": "u",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "ऋ": "ri",
}
_DEV_MATRA = {
    "ा": "a",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ृ": "ri",
}
_ANUSVARA = {"ं": "n", "ँ": "n", "ং": "ng", "ঁ": "n"}
_VIRAMA = {"्", "্"}
_NUKTA = {"़", "়"}

_BN_CONS = {
    "ক": "k",
    "খ": "kh",
    "গ": "g",
    "ঘ": "gh",
    "ঙ": "ng",
    "চ": "ch",
    "ছ": "chh",
    "জ": "j",
    "ঝ": "jh",
    "ঞ": "ny",
    "ট": "t",
    "ঠ": "th",
    "ড": "d",
    "ঢ": "dh",
    "ণ": "n",
    "ত": "t",
    "থ": "th",
    "দ": "d",
    "ধ": "dh",
    "ন": "n",
    "প": "p",
    "ফ": "ph",
    "ব": "b",
    "ভ": "bh",
    "ম": "m",
    "য": "y",
    "র": "r",
    "ল": "l",
    "শ": "sh",
    "ষ": "sh",
    "স": "s",
    "হ": "h",
    "ড়": "r",
    "ঢ়": "rh",
    "য়": "y",
}
_BN_VOWEL = {
    "অ": "a",
    "আ": "a",
    "ই": "i",
    "ঈ": "i",
    "উ": "u",
    "ঊ": "u",
    "এ": "e",
    "ঐ": "oi",
    "ও": "o",
    "ঔ": "ou",
}
_BN_MATRA = {
    "া": "a",
    "ি": "i",
    "ী": "i",
    "ু": "u",
    "ূ": "u",
    "ে": "e",
    "ৈ": "oi",
    "ো": "o",
    "ৌ": "ou",
}
_BN_NUKTA = {"ড": "r", "ঢ": "rh"}

_SKIP = set(" \t\n\r.,;:!?।'\"“”‘’()[]-/")


def _walk(text: str, cons: dict[str, str], nukta: dict[str, str], vowels: dict[str, str], matras: dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _SKIP:
            out.append(" ")
            i += 1
            continue
        if ch in vowels:
            out.append(vowels[ch])
            i += 1
            continue
        if ch in cons:
            base = cons[ch]
            i += 1
            mark = ""
            virama = False
            nasal = ""
            while i < n:
                nxt = text[i]
                if nxt in _NUKTA:
                    base = nukta.get(ch, "r" if base == "d" else base)
                    i += 1
                    continue
                if nxt in matras:
                    mark = matras[nxt]
                    i += 1
                    continue
                if nxt in _VIRAMA:
                    virama = True
                    i += 1
                    continue
                if nxt in _ANUSVARA:
                    nasal = _ANUSVARA[nxt]
                    i += 1
                    continue
                break
            if virama:
                out.append(base)
            elif mark:
                out.append(base + mark)
            else:
                nxt = text[i] if i < n else ""
                # Inherent a between letters; drop it at the end of a word.
                if nxt in cons or nxt in vowels:
                    out.append(base + "a")
                else:
                    out.append(base)
            if nasal:
                out.append(nasal)
            continue
        if ch in _ANUSVARA:
            out.append(_ANUSVARA[ch])
            i += 1
            continue
        if "a" <= ch.lower() <= "z":
            out.append(ch.lower())
        else:
            out.append(" ")
        i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip()


def to_latin(text: str) -> str:
    """Fold Devanagari and Bengali into lowercase Latin. Other letters pass through."""
    if not text:
        return ""
    if re.search(r"[\u0980-\u09FF]", text):
        return _walk(text, _BN_CONS, _BN_NUKTA, _BN_VOWEL, _BN_MATRA)
    if re.search(r"[\u0900-\u097F]", text):
        return _walk(text, _DEV_CONS, _DEV_NUKTA, _DEV_VOWEL, _DEV_MATRA)
    return re.sub(r"[^a-z]+", " ", text.lower()).strip()


def latin_words(text: str) -> list[str]:
    folded = to_latin(text)
    return re.findall(r"[a-z]+", folded)
