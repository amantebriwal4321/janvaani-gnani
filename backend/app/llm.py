"""Optional dialogue extractor. Evon or any OpenAI-compatible chat endpoint.

The model may only fill empty profile fields. Scheme verdicts stay in code.
"""

from __future__ import annotations

import json
import re

import httpx

from app.config import settings
from app.models import BOOL_FIELDS, ENUM_FIELDS, FLOAT_FIELDS, INT_FIELDS, PROFILE_FIELDS, Profile, STRING_FIELDS

SYSTEM = """You extract household facts for an Indian welfare-scheme form.
Return one JSON object and nothing else. Use only fields you actually heard.
Never decide eligibility. Never invent Aadhaar, PAN, or phone numbers.
If a number looks like an ID, omit it.
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
Omit unknown fields. Do not copy fields that are already filled unless the speaker corrected them.
"""


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


class LLMClient:
    """OpenAI-compatible client. LLM_BASE_URL should include /v1, for example http://evon:8000/v1."""

    def __init__(self) -> None:
        self.base = settings.llm_base_url.rstrip("/")
        self.model = settings.llm_model or "evon"
        self.key = settings.llm_api_key

    async def extract_gaps(self, text: str, profile: Profile) -> dict:
        known = {key: value for key, value in profile.model_dump().items() if value is not None}
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {
                    "role": "user",
                    "content": "Already filled:\n"
                    + json.dumps(known, ensure_ascii=False)
                    + "\n\nSpeaker said:\n"
                    + text,
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        url = self.base + "/chat/completions"
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(url, headers=headers, json={**payload, "response_format": {"type": "json_object"}})
            if response.status_code == 400:
                response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        return coerce_patch(_parse_json(content or ""))
