"""One conversational turn: extract, optionally fill gaps with an LLM, then match schemes."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.dialogue import describe_updates, district_spoken, led, mentions_district, say, strip_tags, varied_question
from app.extract import STATES, asks_capability, canonical_state, classify_place_token, extract, polarity_for, yes_no
from app.languages import app_language
from app.llm import clip_reply, remember_failure, reply_matches_language
from app.models import PROFILE_FIELDS, Profile

logger = logging.getLogger("janvaani.engine")
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


_ASK_ORDER = (
    "district",
    "occupation",
    "land_acres",
    "crop",
    "age",
    "senior_age",
    "gender",
    "area",
    "annual_income",
    "bpl",
    "housing",
    "lpg",
    "bank_account",
    "name_match",
    "mobile_linked",
    "aadhaar_seeded",
    "widow",
    "pregnant",
    "category",
    "ration",
)


def _same_line(left: str, right: str) -> bool:
    return " ".join((left or "").split()) == " ".join((right or "").split())


def _upcoming(profile: Profile) -> list[str]:
    names: list[str] = []
    for field in _ASK_ORDER:
        if getattr(profile, field, None) is None:
            names.append(field)
        if len(names) == 4:
            break
    return names


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
        self.ask_counts: dict[str, int] = {}
        self.pending_language_hint: str | None = None
        self.confirm_district: str | None = None
        self.confirm_state: str | None = None
        self.skipped: set[str] = set()

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

    async def utterance(self, text: str, llm, language_hint: str | None = None) -> TurnResult:
        text = (text or "").strip()
        if language_hint is None:
            language_hint = self.pending_language_hint
        self.pending_language_hint = None
        if not text:
            reply = self._avoid_repeat(say("unclear", self.language), 1)
            self.last_reply = reply
            return TurnResult(
                reply=reply,
                tts=reply,
                language=self.language,
                snapshot=self.snapshot(),
            )
        found = extract(text)
        hinted = app_language(language_hint)
        if found.switched_to:
            self.language = found.switched_to
            self.language_locked = True
        elif not self.language_locked:
            detected = hinted or found.language
            if detected:
                self.language = detected

        updated: list[str] = []
        for field, value in found.values.items():
            if field not in PROFILE_FIELDS or field in self.skipped:
                continue
            previous = getattr(self.profile, field)
            setattr(self.profile, field, value)
            self.heard[field] = found.heard.get(field, text[:80])
            if previous != value:
                updated.append(field)
        self._apply_confirm(text, found, updated)

        answer = polarity_for(self.pending, text)
        if (
            answer is not None
            and self.pending
            and self.pending in PROFILE_FIELDS
            and self.pending not in self.skipped
            and not (self.confirm_district and self.pending == "district")
        ):
            setattr(self.profile, self.pending, answer)
            self.heard[self.pending] = text[:80]
            if self.pending not in updated:
                updated.append(self.pending)

        matches_now = match_all(self.profile)
        pending_hint = next_field(self.profile, matches_now, skip=self.skipped)
        if self.confirm_district and self.profile.district is None and "district" not in self.skipped:
            pending_hint = "district"
        scheme_names = [spoken_name(item, self.language) for item in matches_now if item.status in ("qualify", "likely")][:3]
        spoken = ""
        model_fields: dict = {}
        if llm is not None and not found.ignored_id_number:
            try:
                turn = await llm.complete_turn(
                    text=text,
                    profile=self.profile,
                    language=self.language,
                    pending=pending_hint,
                    upcoming=_upcoming(self.profile),
                    last_reply=self.last_reply,
                    scheme_names=scheme_names,
                    confirm_district=self.confirm_district or "",
                )
                model_fields = self._canonicalize_model_fields(turn.fields)
                for field, value in gaps_only(self.profile, model_fields).items():
                    setattr(self.profile, field, value)
                    self.heard[field] = text[:80]
                    updated.append(field)
                spoken = (turn.reply or "").strip()
                if spoken or model_fields:
                    self.llm_status = "used"
                else:
                    self.llm_status = "fallback"
                    logger.warning("llm returned an empty reply and no fields")
            except Exception as exc:
                self.llm_status = "fallback"
                spoken = ""
                remember_failure(exc)
                logger.warning("llm turn fell back: %s", exc.__class__.__name__)
        else:
            self.llm_status = "off" if llm is None else self.llm_status

        if self.profile.district:
            self.confirm_district = None
            self.confirm_state = None

        self.user_turns += 1
        matches = match_all(self.profile)
        level = slip_level(self.profile, matches)
        self.pending = next_field(self.profile, matches, skip=self.skipped)
        if self.confirm_district and self.profile.district is None and "district" not in self.skipped:
            self.pending = "district"
        if updated:
            self.ask_counts.clear()
        elif self.pending:
            self.ask_counts[self.pending] = self.ask_counts.get(self.pending, 0) + 1
            if self.ask_counts[self.pending] > 2:
                self.skipped.add(self.pending)
                if self.pending == "district":
                    self.confirm_district = None
                    self.confirm_state = None
                self.pending = next_field(self.profile, matches, skip=self.skipped)
                if self.pending:
                    self.ask_counts[self.pending] = 1
        variant = 0 if updated or not self.pending else max(0, self.ask_counts.get(self.pending, 1) - 1)
        capability = asks_capability(text)
        display, tts = self._compose(
            updated,
            matches,
            level,
            found.ignored_id_number,
            bool(found.switched_to),
            variant,
            capability,
        )

        # Speak the model whenever the line is usable, including after a field
        # was filled. Eligibility text still comes from the rule engine only
        # when the model line is in the wrong language or repeats the last one.
        use_model = bool(spoken) and reply_matches_language(spoken, self.language) and not _same_line(spoken, self.last_reply)
        if use_model and self.confirm_district and not mentions_district(spoken, self.confirm_district, self.language):
            question = self._question(0)
            if question and question not in spoken:
                spoken = clip_reply(f"{spoken.rstrip()} {question}")
        elif use_model and self.pending and "?" not in spoken and "？" not in spoken:
            question = self._question(variant)
            if question and question not in spoken:
                spoken = clip_reply(f"{spoken.rstrip()} {question}")
        if use_model:
            spoken = clip_reply(spoken)
        if use_model and (not spoken or _same_line(spoken, self.last_reply) or not reply_matches_language(spoken, self.language)):
            use_model = False
        if use_model:
            reply, tts = spoken, spoken
        elif _same_line(display, self.last_reply):
            reply = self._avoid_repeat(display, variant + 1)
            tts = reply
        else:
            reply = display
        self.last_reply = reply
        return TurnResult(reply=reply, tts=tts, language=self.language, snapshot=self.snapshot())

    def _apply_confirm(self, text: str, found, updated: list[str]) -> None:
        """A yes commits the guessed district. A new exact district replaces it."""
        if "district" in found.values or self.profile.district:
            self.confirm_district = None
            self.confirm_state = None
        elif self.confirm_district and "district" not in self.skipped:
            answer = yes_no(text)
            if answer is True:
                self.profile.district = self.confirm_district
                self.heard["district"] = text[:80]
                if self.profile.state is None and self.confirm_state:
                    self.profile.state = self.confirm_state
                    self.profile.state_name = STATES.get(self.confirm_state)
                    self.heard["state_name"] = self.profile.state_name or self.confirm_state
                    updated.append("state")
                    updated.append("state_name")
                updated.append("district")
                self.confirm_district = None
                self.confirm_state = None
            elif answer is False and not found.values:
                self.confirm_district = None
                self.confirm_state = None
        guesses = found.guesses or {}
        if (
            self.profile.district is None
            and self.confirm_district is None
            and guesses.get("district")
            and "district" not in self.skipped
        ):
            self.confirm_district = guesses["district"]
            self.confirm_state = guesses.get("district_state")

    def _canonicalize_model_fields(self, fields: dict) -> dict:
        """An exact district is written. A near miss becomes a confirm, not a silent fill."""
        clean = dict(fields)
        state_token = clean.get("state") or clean.get("state_name")
        if state_token:
            code = canonical_state(str(state_token))
            if code:
                clean["state"] = code
                clean["state_name"] = STATES[code]
            else:
                clean.pop("state", None)
                clean.pop("state_name", None)
        if "district" not in clean:
            return clean
        kind = classify_place_token(str(clean["district"]), clean.get("state") or self.profile.state)
        if kind is None:
            clean.pop("district", None)
            return clean
        if kind[0] == "guess":
            clean.pop("district", None)
            if self.profile.district is None and "district" not in self.skipped:
                self.confirm_district = kind[1]
                self.confirm_state = kind[2]
            return clean
        clean["district"] = kind[1]
        if self.profile.state is None and "state" not in clean:
            clean["state"] = kind[2]
            clean["state_name"] = STATES[kind[2]]
        return clean

    def _question(self, variant: int) -> str:
        if self.confirm_district and self.profile.district is None and "district" not in self.skipped:
            base = say(
                "confirm_district",
                self.language,
                district=district_spoken(self.confirm_district, self.language),
            )
            return led(base, self.language, variant)
        if self.pending == "district" and self.profile.state:
            return led(say("ask_district", self.language), self.language, variant)
        return varied_question(self.pending, self.language, variant)

    def _avoid_repeat(self, current: str, variant: int) -> str:
        unclear_key = ("unclear_b", "unclear_c", "unclear")[variant % 3]
        if self.pending or self.confirm_district:
            line = f"{say(unclear_key, self.language)} {self._question(variant + 1)}"
        else:
            line = say("invite", self.language)
        cleaned = strip_tags(line)
        if _same_line(cleaned, current) or _same_line(cleaned, self.last_reply):
            cleaned = strip_tags(f"{say('ack', self.language)} {self._question(variant + 2)}")
        return cleaned

    def _compose(
        self,
        updated,
        matches,
        level,
        ignored: bool,
        switched: bool,
        variant: int = 0,
        capability: bool = False,
    ) -> tuple[str, str]:
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
            if capability:
                parts.append(say("can_do", lang))
            else:
                parts.append(say(("unclear", "unclear_b", "unclear_c")[variant % 3], lang))
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
        elif self.pending or self.confirm_district:
            parts.append(self._question(variant))
        else:
            parts.append(say("invite", lang))

        display = strip_tags(" ".join(part for part in parts if part))
        # Timbre accepts <pauses> but does not speak it, and Prisma splits the
        # utterance on that gap. Speak the sentences as one line.
        tts = " ".join(part for part in parts if part)
        return display, tts


def echo_of_assistant(user_text: str, assistant_text: str) -> bool:
    """Drop a transcript that is just the assistant's own voice leaking into the mic."""
    user = strip_tags(user_text).casefold().strip()
    assistant = strip_tags(assistant_text).casefold().strip()
    if len(user) < 12 or not assistant:
        return False
    return user in assistant
