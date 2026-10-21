"""OpenAI-compatible phrasing and field extraction. Groq by default.

The model may fill empty profile fields and choose the words. Scheme verdicts
stay in the rule engine. A missing key, or any error, leaves that turn to the
deterministic lines. The error is kept for /api/health and the log.

llama-3.1-8b-instant was removed from Groq's free and developer tiers on
2026-08-16. A request that the host rejects as an unknown model is tried once
more with openai/gpt-oss-20b, and that id is reused for the rest of the process.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings
from app.models import BOOL_FIELDS, ENUM_FIELDS, FLOAT_FIELDS, INT_FIELDS, PROFILE_FIELDS, Profile, STRING_FIELDS

logger = logging.getLogger("janvaani.llm")

REPLACEMENT_MODEL = "openai/gpt-oss-20b"
_REJECT_PHRASES = (
    "decommissioned",
    "not found",
    "does not exist",
    "do not exist",
    "unknown model",
    "invalid model",
    "model_not_found",
    "no such model",
    "model is not",
    "unsupported model",
)

# Process-wide. A rejected model id is not requested again after one failure.
_last_error = ""
_notice = ""
_active_model = ""

SYSTEM = """You are Shivani, speaking for JanVaani on a phone call about Indian government schemes.
You are warm, patient, and brief, the way a kind person at a help desk would be.

Return one JSON object and nothing else:
{"reply":"...","fields":{}}

How to speak:
- Answer what the person actually just said, first, in one short sentence, in their language. If they asked something, answer that. If they only greeted you, greet them back. If you do not know, say so kindly in a few words.
- If they ask what you can do, say in one sentence that you fill the scheme form and make a slip for the CSC. Then ask the next missing field.
- If confirm_district is set, that district is only a guess. Ask whether that district is theirs. Do not ask which district and state.
- Then ask for the next missing form field, in the same language. One question only.
- Two short sentences at most. No lists, no markdown, nothing that is hard to say aloud.
- Never repeat the previous reply word for word. Vary the wording.
- Language codes: hi Hindi in Devanagari, hi-en Hinglish in Latin letters, en English, kn Kannada, te Telugu, ta Tamil, mr Marathi, bn Bengali, ml Malayalam.

What you must not do:
- Do not decide who qualifies for a scheme. You may mention a scheme name only if it is in the list you are given, and only once. Never invent a scheme. Never say eligible or not eligible from your own judgment.
- Do not ask for Aadhaar, PAN, or a phone number. Never invent those. If a number looks like an ID, omit it.
- fields may contain only facts you actually heard. Omit unknown fields. Do not repeat a field that is already filled unless the speaker corrected it.

Fields and types:
- age, senior_age, annual_income: integers. annual_income is rupees per year.
- land_acres: number
- gender: woman | man | other
- area: rural | urban
- occupation: farmer | artisan | street_vendor | labourer | homemaker | student | salaried | other
- ration: aay | phh | nphh | none
- housing: kutcha | pucca | homeless
- category: sc | st | obc | general
- crop, artisan_trade, district, state_name: short strings
- state: two-letter code such as KA, MH, TG, TN, WB, KL
- bpl, crop_loss, widow, disability, pregnant, bank_account, aadhaar_seeded, mobile_linked, name_match, lpg: true or false
"""

_SCRIPTS = {
    "hi": r"[\u0900-\u097F]",
    "mr": r"[\u0900-\u097F]",
    "kn": r"[\u0C80-\u0CFF]",
    "te": r"[\u0C00-\u0C7F]",
    "ta": r"[\u0B80-\u0BFF]",
    "bn": r"[\u0980-\u09FF]",
    "ml": r"[\u0D00-\u0D7F]",
}


@dataclass
class LLMTurn:
    fields: dict
    reply: str


def _parse_json(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        return {}
    data = json.loads(content[start : end + 1])
    return data if isinstance(data, dict) else {}


def _as_bool(value) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"true", "yes", "haan", "y"}:
            return True
        if token in {"false", "no", "nahi", "n"}:
            return False
    return None


def coerce_patch(data: dict) -> dict:
    clean = {}
    for key, value in data.items():
        if key not in PROFILE_FIELDS or value is None:
            continue
        if isinstance(value, str) and re.search(r"\d{10,}", value):
            continue
        if key in BOOL_FIELDS:
            parsed = _as_bool(value)
            if parsed is not None:
                clean[key] = parsed
        elif key in INT_FIELDS:
            try:
                clean[key] = int(float(value))
            except (TypeError, ValueError):
                continue
        elif key in FLOAT_FIELDS:
            try:
                clean[key] = float(value)
            except (TypeError, ValueError):
                continue
        elif key in ENUM_FIELDS:
            token = str(value).strip().lower()
            if token in ENUM_FIELDS[key]:
                clean[key] = token
        elif key in STRING_FIELDS:
            token = str(value).strip()
            if token and len(token) <= 80:
                clean[key] = token
    return clean


def clip_reply(text: str, limit: int = 280) -> str:
    """Keep a spoken line short enough for one breath of TTS."""
    cleaned = re.sub(r"\s+", " ", (text or "")).strip().strip("`")
    if len(cleaned) <= limit:
        return cleaned
    cut = cleaned[:limit]
    for sep in ("।", "?", "!", "."):
        index = cut.rfind(sep)
        if index >= 40:
            return cut[: index + 1].strip()
    return cut.rstrip()


def reply_matches_language(reply: str, language: str) -> bool:
    """True when the line is in the language Timbre and the device voice will speak."""
    if not reply or not reply.strip():
        return False
    if language in ("en", "hi-en"):
        return re.search(r"[A-Za-z]", reply) is not None
    pattern = _SCRIPTS.get(language)
    if pattern is None:
        return True
    return re.search(pattern, reply) is not None


def llm_health() -> dict[str, str]:
    """Model actually in use, the last failure, and a failover note. No secrets."""
    model = _active_model or settings.llm_model or REPLACEMENT_MODEL
    return {"model": model, "error": _last_error, "notice": _notice}


def remember_failure(exc: BaseException) -> None:
    """Record an engine-level failure when the client did not already."""
    if _last_error:
        return
    text = str(exc).strip() or exc.__class__.__name__
    _set_error(text)


def _scrub(text: str) -> str:
    cleaned = re.sub(r"Bearer\s+\S+", "Bearer [redacted]", text or "", flags=re.I)
    key = (settings.llm_api_key or "").strip()
    if key:
        cleaned = cleaned.replace(key, "[redacted]")
    return re.sub(r"\s+", " ", cleaned).strip()


def _set_error(text: str) -> None:
    global _last_error
    _last_error = _scrub(text)[:180]
    logger.warning("llm call failed: %s", _last_error)


def _set_notice(text: str) -> None:
    global _notice
    _notice = _scrub(text)[:180]
    logger.warning("llm notice: %s", _notice)


def _clear_error() -> None:
    global _last_error
    _last_error = ""


def _remember_model(model: str) -> None:
    global _active_model
    _active_model = model


class _ModelRejected(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _model_rejected(status: int, body: str) -> bool:
    if status not in (400, 404):
        return False
    text = (body or "").lower()
    if "response_format" in text or "json_object" in text or "json mode" in text:
        return False
    return any(phrase in text for phrase in _REJECT_PHRASES)


def _public_http(status: int, body: str) -> str:
    return _scrub(f"HTTP {status}: {body}")[:180]


def _message_text(body: dict) -> str:
    message = body["choices"][0]["message"] or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        bits = []
        for part in content:
            if isinstance(part, dict):
                bits.append(str(part.get("text") or ""))
            else:
                bits.append(str(part))
        content = "".join(bits)
    content = re.sub(r"<think>.*?</think>", "", str(content), flags=re.S).strip()
    if content:
        return content
    reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
    return re.sub(r"<think>.*?</think>", "", str(reasoning), flags=re.S).strip()


class LLMClient:
    """OpenAI-compatible client. LLM_BASE_URL includes /v1, for example https://api.groq.com/openai/v1."""

    def __init__(self) -> None:
        self.base = settings.llm_base_url.rstrip("/")
        self.model = _active_model or settings.llm_model or REPLACEMENT_MODEL
        self.key = settings.llm_api_key

    async def complete_turn(
        self,
        text: str,
        profile: Profile,
        language: str,
        pending: str | None,
        upcoming: list[str],
        last_reply: str,
        scheme_names: list[str],
        confirm_district: str = "",
    ) -> LLMTurn:
        known = {key: value for key, value in profile.model_dump().items() if value is not None}
        payload = {
            "temperature": 0.4,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "language": language,
                            "already_filled": known,
                            "next_field": pending,
                            "also_missing": upcoming,
                            "scheme_names_already_decided": scheme_names,
                            "previous_reply": last_reply,
                            "confirm_district": confirm_district,
                            "speaker_said": text,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        content = await self._chat(payload)
        try:
            data = _parse_json(content or "")
        except json.JSONDecodeError as exc:
            _set_error(f"json parse: {exc}")
            raise
        raw_fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
        if not raw_fields:
            raw_fields = {key: value for key, value in data.items() if key not in {"reply", "text"}}
        reply = clip_reply(str(data.get("reply") or data.get("text") or ""))
        fields = coerce_patch(raw_fields)
        if not reply and not fields:
            _set_error("empty reply")
        else:
            _clear_error()
        return LLMTurn(fields=fields, reply=reply)

    async def extract_gaps(self, text: str, profile: Profile) -> dict:
        turn = await self.complete_turn(text, profile, "hi", None, [], "", [])
        return turn.fields

    async def _chat(self, payload: dict) -> str:
        try:
            return await self._post(payload, self.model)
        except _ModelRejected as exc:
            if self.model == REPLACEMENT_MODEL:
                _set_error(exc.detail)
                raise
            logger.warning("llm model rejected: %s; retrying %s", exc.detail, REPLACEMENT_MODEL)
            _set_notice(f"{self.model} was rejected: {exc.detail}. Using {REPLACEMENT_MODEL}.")
            _remember_model(REPLACEMENT_MODEL)
            self.model = REPLACEMENT_MODEL
            return await self._post(payload, REPLACEMENT_MODEL)

    async def _post(self, payload: dict, model: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        url = self.base + "/chat/completions"
        body = {**payload, "model": model}
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={**body, "response_format": {"type": "json_object"}},
                )
                if _model_rejected(response.status_code, getattr(response, "text", "")):
                    raise _ModelRejected(_public_http(response.status_code, response.text))
                if response.status_code == 400:
                    response = await client.post(url, headers=headers, json=body)
                    if _model_rejected(response.status_code, getattr(response, "text", "")):
                        raise _ModelRejected(_public_http(response.status_code, response.text))
                if response.status_code >= 400:
                    _set_error(_public_http(response.status_code, getattr(response, "text", "")))
                    response.raise_for_status()
                data = response.json()
        except _ModelRejected:
            raise
        except httpx.TimeoutException:
            _set_error("timeout")
            raise
        except httpx.HTTPError as exc:
            if not _last_error:
                _set_error(str(exc) or exc.__class__.__name__)
            raise
        text = _message_text(data)
        _remember_model(model)
        return text
