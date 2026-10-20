"""One conversational turn: extract, optionally fill gaps with an LLM, then match schemes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.dialogue import describe_updates, question_for, say, strip_tags
from app.extract import extract, polarity_for
from app.models import PROFILE_FIELDS, Profile
from app.schemes import (
    csc_text,
    documents_for,
    fix_first,
    match_all,
    next_field,
    slip_level,
    spoken_name,
)


def _inr(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    digits = str(abs(int(amount)))
    if len(digits) <= 3:
        return f"Rs {sign}{digits}"
    head, tail = digits[:-3], digits[-3:]
    parts: list[str] = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    if head:
        parts.append(head)
    return "Rs " + sign + ",".join(reversed(parts)) + "," + tail


DISPLAY = (
    ("district", "District"),
    ("state_name", "State"),
    ("area", "Area type"),
    ("occupation", "Occupation"),
    ("artisan_trade", "Trade"),
    ("land_acres", "Land"),
    ("crop", "Crop"),
    ("crop_loss", "Crop loss this season"),
    ("age", "Age"),
    ("senior_age", "Eldest family member"),
    ("gender", "Gender"),
    ("category", "Social category"),
    ("annual_income", "Annual family income"),
    ("bpl", "BPL"),
    ("ration", "Ration card"),
    ("housing", "House"),
    ("lpg", "LPG connection"),
    ("widow", "Widow"),
    ("disability", "Disability"),
    ("pregnant", "Pregnancy or new mother"),
    ("bank_account", "Bank account"),
    ("aadhaar_seeded", "Aadhaar seeded in bank"),
    ("mobile_linked", "Mobile linked to Aadhaar"),
    ("name_match", "Aadhaar and ration name match"),
)

VALUE_WORDS = {
    "area": {"rural": "Rural", "urban": "Urban"},
    "occupation": {
        "farmer": "Farmer",
        "artisan": "Artisan",
        "street_vendor": "Street vendor",
        "labourer": "Wage worker",
        "homemaker": "Homemaker",
        "student": "Student",
        "salaried": "Salaried",
        "other": "Other",
    },
    "gender": {"woman": "Woman", "man": "Man", "other": "Other"},
    "ration": {"aay": "AAY (Antyodaya)", "phh": "PHH", "nphh": "NPHH", "none": "None"},
    "housing": {"kutcha": "Kutcha", "pucca": "Pucca", "homeless": "No house"},
    "category": {"sc": "SC", "st": "ST", "obc": "OBC", "general": "General"},
}


def format_value(field: str, value) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if field == "land_acres":
        return f"{float(value):g} acres"
    if field == "annual_income":
        return _inr(int(value))
    if field in VALUE_WORDS:
        return VALUE_WORDS[field].get(value, str(value))
    if field == "crop":
        return str(value).title()
    if field == "artisan_trade":
        return str(value).title()
    return str(value)


def profile_rows(profile: Profile, heard: dict) -> list[dict]:
    rows = []
    for field, label in DISPLAY:
        raw = getattr(profile, field)
        if raw is None:
            continue
        rows.append(
            {
                "field": field,
                "label": label,
                "value": format_value(field, raw),
                "heard": heard.get(field),
            }
        )
    return rows


def share_text(ref: str, profile: Profile, matches, documents: list[str], fixes: list[str]) -> str:
    good = [item for item in matches if item.status in ("qualify", "likely")]
    place = ", ".join(bit for bit in (profile.district, profile.state_name) if bit) or "Place not filled yet"
    lines = [f"JanVaani slip {ref}", place]
    if good:
        lines.append("Apply: " + ", ".join(item.name for item in good))
    else:
        lines.append("Apply: nothing confirmed yet")
    if fixes:
        lines.append("Fix first: " + " ".join(fixes))
    if documents:
        lines.append("Carry: " + ", ".join(documents))
    lines.append(csc_text(profile).split(".")[0] + ".")
    lines.append("Indicative only. Practice slip. No Aadhaar number is stored.")
    return "\n".join(lines)


def gaps_only(profile: Profile, patch: dict) -> dict:
    """LLM fills may not overwrite a field the rules already set."""
    clean = {}
    for key, value in patch.items():
        if key not in PROFILE_FIELDS or value is None:
            continue
        if getattr(profile, key) is None:
            clean[key] = value
    return clean


@dataclass
class TurnResult:
    reply: str
    tts: str
    language: str
    snapshot: dict


class Brain:
    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex
        self.ref = "JV-" + uuid.uuid4().hex[:4].upper()
        self.profile = Profile()
        self.heard: dict[str, str] = {}
        self.language = "hi"
        self.language_locked = False
        self.pending: str | None = None
        self.user_turns = 0
        self.llm_status = "off"
        self.last_reply = ""

    def set_language(self, code: str) -> None:
        if code in ("", "auto", None):
            self.language_locked = False
            if not self.user_turns:
                self.language = "hi"
            return
        self.language = code
        self.language_locked = True

    def snapshot(self) -> dict:
        matches = match_all(self.profile)
        documents = documents_for(matches)
        fixes = fix_first(self.profile)
        level = slip_level(self.profile, matches)
        return {
            "session_id": self.session_id,
            "ref": self.ref,
            "language": self.language,
            "language_locked": self.language_locked,
            "profile": self.profile.model_dump(),
            "rows": profile_rows(self.profile, self.heard),
            "heard": self.heard,
            "matches": [item.as_dict() for item in matches],
            "documents": documents,
            "fix_first": fixes,
            "csc": csc_text(self.profile),
            "slip": level,
            "pending": self.pending,
            "share_text": share_text(self.ref, self.profile, matches, documents, fixes),
            "llm": self.llm_status,
            "user_turns": self.user_turns,
            "scheme_count": len(matches),
        }

    def greet(self) -> TurnResult:
        reply = say("greeting", self.language)
        self.last_reply = reply
        tts = reply
        return TurnResult(reply=reply, tts=tts, language=self.language, snapshot=self.snapshot())

    async def utterance(self, text: str, llm) -> TurnResult:
        text = (text or "").strip()
        if not text:
            return TurnResult(
                reply=say("unclear", self.language),
                tts=say("unclear", self.language),
                language=self.language,
                snapshot=self.snapshot(),
            )
        found = extract(text)
        if found.switched_to:
            self.language = found.switched_to
            self.language_locked = True
        elif found.language and not self.language_locked:
            self.language = found.language

        updated: list[str] = []
        for field, value in found.values.items():
            if field not in PROFILE_FIELDS:
                continue
            setattr(self.profile, field, value)
            self.heard[field] = found.heard.get(field, text[:80])
            updated.append(field)

        answer = polarity_for(self.pending, text)
        if answer is not None and self.pending and self.pending in PROFILE_FIELDS:
            setattr(self.profile, self.pending, answer)
            self.heard[self.pending] = text[:80]
            if self.pending not in updated:
                updated.append(self.pending)

        if llm is not None and not found.ignored_id_number:
            try:
                patch = await llm.extract_gaps(text, self.profile)
                for field, value in gaps_only(self.profile, patch).items():
                    setattr(self.profile, field, value)
                    self.heard[field] = text[:80]
                    updated.append(field)
                self.llm_status = "used"
            except Exception:
                self.llm_status = "fallback"
        else:
            self.llm_status = "off" if llm is None else self.llm_status

        self.user_turns += 1
        matches = match_all(self.profile)
        self.pending = next_field(self.profile, matches)
        level = slip_level(self.profile, matches)
        reply, tts = self._compose(updated, matches, level, found.ignored_id_number, bool(found.switched_to))
        self.last_reply = reply
        return TurnResult(reply=reply, tts=tts, language=self.language, snapshot=self.snapshot())

    def _compose(self, updated, matches, level, ignored: bool, switched: bool) -> tuple[str, str]:
        lang = self.language
        parts: list[str] = []
        if ignored:
            parts.append(say("id_ignored", lang))
        if switched:
            parts.append(say("switched", lang))
        facts = describe_updates(self.profile, updated, lang)
        audit = {"name_match", "mobile_linked", "bank_account", "aadhaar_seeded"}
        fresh = [field for field in updated if field not in audit]
        if facts and (fresh or "name_match" in updated or "bank_account" in updated):
            parts.append(say("heard", lang, facts=facts))
        good = [item for item in matches if item.status in ("qualify", "likely")]
        names = [spoken_name(item, lang) for item in good[:3]]
        scheme_text = ", ".join(names)
        if len(good) > 3:
            scheme_text += say("and_more", lang, n=len(good) - 3)
        if fresh and good:
            parts.append(say("schemes_line", lang, schemes=scheme_text))
        if not updated and not switched and not ignored:
            parts.append(say("unclear", lang))
        elif updated and not facts and not switched:
            parts.append(say("ack", lang))

        if level == "ready" and self.pending is None:
            parts.append(say("slip_ready", lang, schemes=scheme_text or say("invite", lang)))
            if self.profile.name_match is False:
                parts.append(say("fix_name", lang))
            if self.profile.mobile_linked is False:
                parts.append(say("fix_mobile", lang))
            if self.profile.bank_account is False:
                parts.append(say("fix_bank", lang))
        elif self.pending:
            parts.append(question_for(self.pending, lang))
        else:
            parts.append(say("invite", lang))

        display = strip_tags(" ".join(part for part in parts if part))
        tts = " <pauses> ".join(part for part in parts if part)
        return display, tts


def echo_of_assistant(user_text: str, assistant_text: str) -> bool:
    """Drop a transcript that is just the assistant's own voice leaking into the mic."""
    user = strip_tags(user_text).casefold().strip()
    assistant = strip_tags(assistant_text).casefold().strip()
    if len(user) < 12 or not assistant:
        return False
    return user in assistant
