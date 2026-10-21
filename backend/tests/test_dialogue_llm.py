"""Phrasing stays helpful when the caller asks something off the form.

Eligibility stays in the rule engine. The model may only fill empty fields and
choose words. A missing model, or a bad reply, falls back to varied lines.
"""

import asyncio

from fastapi.testclient import TestClient

from app.config import settings
from app.engine import Brain
from app.languages import app_language
from app.llm import LLMTurn
from app.main import app
from app.models import Profile


class _Reply:
    def __init__(self, reply: str, fields: dict | None = None) -> None:
        self.reply = reply
        self.fields = fields or {}
        self.calls = 0

    async def complete_turn(self, **kwargs) -> LLMTurn:
        self.calls += 1
        self.last = kwargs
        return LLMTurn(fields=dict(self.fields), reply=self.reply)


class _Boom:
    async def complete_turn(self, **kwargs) -> LLMTurn:
        raise RuntimeError("llm down")


def _run(coro):
    return asyncio.run(coro)


def test_language_tags_map_onto_call_languages():
    assert app_language("en-IN") == "en"
    assert app_language("kn_IN") == "kn"
    assert app_language("hi-Latn") == "hi-en"
    assert app_language("indic-auto") is None
    assert app_language("") is None


def test_unrelated_questions_do_not_repeat_the_same_line():
    brain = Brain()
    brain.set_language("hi")

    async def run():
        first = await brain.utterance("आज मौसम कैसा है?", None)
        second = await brain.utterance("आप कौन हो?", None)
        assert first.reply != second.reply
        assert "राज्य" in first.reply
        assert "राज्य" in second.reply
        assert "मैं फिर से सुनना चाहती हूँ" in first.reply
        assert "मैं फिर से सुनना चाहती हूँ" not in second.reply
        assert brain.llm_status == "off"
        assert brain.profile.district is None

    _run(run())


def test_model_reply_answers_before_the_next_field():
    brain = Brain()
    brain.set_language("hi")
    line = "मौसम मैं नहीं बता सकती। आप किस ज़िले और राज्य से हैं?"
    model = _Reply(line)

    async def run():
        result = await brain.utterance("आज मौसम कैसा है?", model)
        assert result.reply == line
        assert brain.llm_status == "used"
        assert model.calls == 1
        assert model.last["language"] == "hi"
        assert model.last["pending"] == "district"
        assert "eligible" not in model.last

    _run(run())


def test_identical_model_reply_is_not_spoken_twice():
    brain = Brain()
    brain.set_language("hi")
    line = "मैं योजना देखती हूँ। आप किस ज़िले और राज्य से हैं?"
    model = _Reply(line)

    async def run():
        first = await brain.utterance("आज मौसम कैसा है?", model)
        second = await brain.utterance("आप कौन हो?", model)
        assert first.reply == line
        assert second.reply != first.reply
        assert "राज्य" in second.reply

    _run(run())


def test_model_error_falls_back_to_the_form():
    brain = Brain()
    brain.set_language("en")

    async def run():
        result = await brain.utterance("what is the weather today?", _Boom())
        assert brain.llm_status == "fallback"
        assert brain.language == "en"
        assert "district" in result.reply.lower()

    _run(run())


def test_model_cannot_change_a_rule_or_invent_eligibility():
    brain = Brain()
    brain.set_language("hi")
    brain.profile = Profile(occupation="farmer", district="Kolar", state="KA", state_name="Karnataka", land_acres=2)
    model = _Reply(
        "You are eligible for a made-up scheme.",
        {"occupation": "salaried", "crop": "ragi", "aadhaar": "123412341234"},
    )

    async def run():
        result = await brain.utterance("बस यूँ ही पूछ रहा हूँ", model)
        assert brain.profile.occupation == "farmer"
        assert brain.profile.crop == "ragi"
        assert "made-up" not in result.reply
        assert brain.llm_status == "used"

    _run(run())


def test_auto_mode_follows_each_utterance_including_english():
    brain = Brain()

    async def run():
        english = await brain.utterance("What can you help me with?", None)
        assert brain.language == "en"
        assert brain.language_locked is False
        assert "district" in english.reply.lower()
        await brain.utterance("ನಾನು ಮೈಸೂರಿನ ರೈತ", None)
        assert brain.language == "kn"
        hinted = await Brain().utterance("नमस्ते", None, language_hint="en-IN")
        assert hinted.language == "en"
        locked = Brain()
        locked.set_language("kn")
        await locked.utterance("hello there my friend", None, language_hint="en-IN")
        assert locked.language == "kn"

    _run(run())


def test_groq_stays_off_until_the_key_is_set(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", "auto")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.groq.com/openai/v1")
    assert settings.llm_on is False
    monkeypatch.setattr(settings, "llm_api_key", "gsk-test")
    assert settings.llm_on is True
    monkeypatch.setattr(settings, "llm_enabled", "off")
    assert settings.llm_on is False
    monkeypatch.setattr(settings, "llm_enabled", "auto")
    monkeypatch.setattr(settings, "llm_base_url", "http://127.0.0.1:9/v1")
    monkeypatch.setattr(settings, "llm_api_key", "")
    assert settings.llm_on is True
    monkeypatch.setattr(settings, "llm_base_url", "")
    assert settings.llm_on is False


def test_warm_skips_timbre_without_a_key(monkeypatch):
    monkeypatch.setattr(settings, "gnani_api_key", "")
    with TestClient(app) as client:
        response = client.post("/api/warm", json={"language": "en"})
    assert response.status_code == 200
    body = response.json()
    assert body["warmed"] is False
    assert body["speech"] == "mock"


def test_warm_prefetches_the_greeting(monkeypatch):
    monkeypatch.setattr(settings, "gnani_api_key", "test-key")
    seen: dict = {}

    async def fake(text: str, language: str) -> None:
        seen["text"] = text
        seen["language"] = language

    monkeypatch.setattr("app.gnani.warm_tts", fake)
    with TestClient(app) as client:
        response = client.post("/api/warm", json={"language": "en"})
        assert response.status_code == 200
        assert response.json()["warmed"] is True
        assert seen["language"] == "en"
        assert "JanVaani" in seen["text"]
        auto = client.post("/api/warm", json={"language": "auto"})
        assert auto.json()["language"] == "hi"
        assert seen["language"] == "hi"
