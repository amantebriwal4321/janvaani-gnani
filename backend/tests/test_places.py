"""Place names from messy speech, and a model reply that is actually spoken.

The two lines below are the ones that failed on the phone: a clean Pakur
sentence was asked again, and a capability question got the fixed reprompt.
"""

import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.engine import Brain
from app.extract import extract
from app.llm import LLMTurn
from app.main import app
from app.models import Profile
import app.llm as llm_mod


def _run(coro):
    return asyncio.run(coro)


def _clear_llm_status() -> None:
    llm_mod._last_error = ""
    llm_mod._notice = ""
    llm_mod._active_model = ""


def test_pakar_sets_jharkhand_and_asks_before_writing_the_district():
    found = extract("मैं झारखंड के पाकड़ से हूँ।")
    assert found.values["state"] == "JH"
    assert found.values["state_name"] == "Jharkhand"
    assert "district" not in found.values
    assert found.guesses["district"] == "Pakur"
    assert found.guesses["district_state"] == "JH"

    mangled = extract("मैं पापड़, जो राज्य और झारखंड से हूँ")
    assert mangled.values["state"] == "JH"
    assert mangled.guesses["district"] == "Pakur"

    exact = extract("मैं पाकुड़ से हूँ")
    assert exact.values["district"] == "Pakur"
    assert exact.values["state"] == "JH"


def test_bengali_bankura_keeps_the_named_state():
    found = extract("বাঁকুড়া জেলা, ঝাড়খণ্ড রাজ্য")
    assert found.values["district"] == "Bankura"
    assert found.values["state"] == "JH"
    assert found.values["state_name"] == "Jharkhand"
    assert found.language == "bn"


def test_yes_confirms_pakur_and_a_capability_question_is_answered():
    brain = Brain()
    brain.set_language("hi")

    async def run():
        asked = await brain.utterance("तुम क्या क्या कर सकती हो?", None)
        assert "फ़ॉर्म" in asked.reply or "फॉर्म" in asked.reply
        assert "फिर से सुनना" not in asked.reply
        assert brain.llm_status == "off"

        place = await brain.utterance("मैं झारखंड के पाकड़ से हूँ।", None)
        assert "पाकुड़" in place.reply
        assert "फिर से सुनना" not in place.reply
        assert "किस ज़िले और राज्य" not in place.reply
        assert brain.profile.state == "JH"
        assert brain.profile.state_name == "Jharkhand"
        assert brain.profile.district is None
        assert brain.pending == "district"

        await brain.utterance("हाँ", None)
        assert brain.profile.district == "Pakur"
        assert brain.profile.state == "JH"
        assert brain.pending != "district"

    _run(run())


def test_model_reply_is_kept_after_a_field_is_filled():
    brain = Brain()
    brain.set_language("hi")

    class _Reply:
        def __init__(self) -> None:
            self.calls = 0

        async def complete_turn(self, **kwargs) -> LLMTurn:
            self.calls += 1
            return LLMTurn(fields={}, reply="झारखंड लिख लिया। आगे बताइए।")

    model = _Reply()

    async def run():
        result = await brain.utterance("मैं झारखंड के पाकड़ से हूँ।", model)
        assert model.calls == 1
        assert result.reply.startswith("झारखंड लिख लिया")
        assert "पाकुड़" in result.reply
        assert brain.llm_status == "used"
        assert brain.profile.state == "JH"
        assert brain.profile.district is None
        assert model.calls == 1

    _run(run())


def test_a_fuzzy_model_district_is_confirmed_not_written():
    brain = Brain()
    brain.set_language("hi")

    class _Reply:
        async def complete_turn(self, **kwargs) -> LLMTurn:
            return LLMTurn(fields={"district": "pakar", "state": "Jharkhand"}, reply="ठीक है, नोट किया।")

    async def run():
        await brain.utterance("बस सुन लीजिए", _Reply())
        assert brain.profile.state == "JH"
        assert brain.profile.district is None
        assert brain.confirm_district == "Pakur"

    _run(run())


def test_the_same_field_is_skipped_after_two_asks():
    brain = Brain()
    brain.set_language("hi")

    async def run():
        await brain.utterance("आज मौसम कैसा है?", None)
        await brain.utterance("आप कौन हो?", None)
        assert brain.pending == "district"
        third = await brain.utterance("कुछ और नहीं", None)
        assert brain.pending != "district"
        assert "district" in brain.skipped
        assert "किस ज़िले और राज्य" not in third.reply

    _run(run())


def test_rejected_groq_model_is_retried_and_shown_on_health(monkeypatch):
    _clear_llm_status()
    monkeypatch.setattr(settings, "llm_model", "llama-3.1-8b-instant")
    monkeypatch.setattr(settings, "llm_api_key", "gsk-test")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "llm_enabled", "auto")
    calls: list[str] = []

    class Resp:
        def __init__(self, status: int, payload: dict) -> None:
            self.status_code = status
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
                response = httpx.Response(self.status_code, request=request, text=self.text)
                raise httpx.HTTPStatusError("bad", request=request, response=response)

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            assert headers["Authorization"] == "Bearer gsk-test"
            assert "gsk-test" not in str(json)
            calls.append(json["model"])
            if json["model"] == "llama-3.1-8b-instant":
                return Resp(400, {"error": {"message": "The model has been decommissioned"}})
            return Resp(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "reasoning": "<think>draft</think>"
                                '{"reply":"मैं योजना का फ़ॉर्म भरती हूँ।","fields":{}}',
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", Client)
    try:
        client = llm_mod.LLMClient()
        turn = _run(
            client.complete_turn(
                "तुम क्या क्या कर सकती हो?",
                Profile(),
                "hi",
                "district",
                [],
                "",
                [],
            )
        )
        assert calls == ["llama-3.1-8b-instant", "openai/gpt-oss-20b"]
        assert "फ़ॉर्म" in turn.reply
        assert llm_mod._active_model == "openai/gpt-oss-20b"
        assert llm_mod._last_error == ""
        assert "llama-3.1-8b-instant" in llm_mod._notice
        assert "openai/gpt-oss-20b" in llm_mod._notice
        assert llm_mod.LLMClient().model == "openai/gpt-oss-20b"

        with TestClient(app) as api:
            body = api.get("/api/health").json()
        assert body["llm"] == "openai/gpt-oss-20b"
        assert body["llm_error"] == ""
        assert "rejected" in body["llm_notice"]
    finally:
        _clear_llm_status()


def test_timeout_and_bad_json_are_surfaced(monkeypatch):
    _clear_llm_status()

    class Client:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", Client)
    try:
        try:
            _run(llm_mod.LLMClient().complete_turn("नमस्ते", Profile(), "hi", None, [], "", []))
        except httpx.TimeoutException:
            pass
        else:
            raise AssertionError("timeout should raise")
        assert llm_mod._last_error == "timeout"

        class Ok:
            def __init__(self, *args, **kwargs) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, url, headers=None, json=None):
                class Resp:
                    status_code = 200
                    text = "{not json}"

                    def json(self):
                        return {"choices": [{"message": {"content": "{not json}"}}]}

                    def raise_for_status(self) -> None:
                        return None

                return Resp()

        monkeypatch.setattr(llm_mod.httpx, "AsyncClient", Ok)
        try:
            _run(llm_mod.LLMClient().complete_turn("नमस्ते", Profile(), "hi", None, [], "", []))
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("bad json should raise")
        assert llm_mod._last_error.startswith("json parse:")
        with TestClient(app) as api:
            body = api.get("/api/health").json()
        assert "json parse" in body["llm_error"]
        assert "gsk" not in body["llm_error"]
    finally:
        _clear_llm_status()


class _SocketModel:
    def __init__(self) -> None:
        self.seen: list[str] = []

    async def complete_turn(self, **kwargs) -> LLMTurn:
        self.seen.append(kwargs["text"])
        if "कर सकती" in kwargs["text"]:
            return LLMTurn(
                fields={},
                reply="मैं योजना का फ़ॉर्म भरती हूँ, और सीएससी के लिए पर्ची बनाती हूँ।",
            )
        return LLMTurn(fields={"state": "JH"}, reply="झारखंड लिख लिया।")


def test_live_websocket_answers_both_phone_utterances(monkeypatch):
    """Same socket the phone uses. The model reply is kept, and Pakur is confirmed."""
    monkeypatch.setattr(settings, "gnani_api_key", "")
    monkeypatch.setattr(settings, "llm_api_key", "gsk-test")
    monkeypatch.setattr(settings, "llm_base_url", "https://api.groq.com/openai/v1")
    monkeypatch.setattr(settings, "llm_enabled", "auto")
    model = _SocketModel()
    monkeypatch.setattr("app.session.LLMClient", lambda: model)

    def take(ws, turns: int) -> tuple[str, dict]:
        state = {}
        seen_state = False
        for _ in range(16):
            message = ws.receive_json()
            if message.get("type") == "transcript" and message.get("role") == "user":
                seen_state = False
                state = {}
            if message.get("type") == "state" and message["state"]["user_turns"] >= turns:
                state = message["state"]
                seen_state = True
            if seen_state and message.get("type") == "transcript" and message.get("role") == "assistant":
                return message["text"], state
        raise AssertionError(state)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/call") as ws:
            ws.send_json({"type": "start", "language": "hi"})
            ready = None
            for _ in range(8):
                message = ws.receive_json()
                if message.get("type") == "ready":
                    ready = message
                    break
            assert ready is not None and ready["language"] == "hi"
            for _ in range(6):
                if ws.receive_json().get("type") == "speak":
                    break

            ws.send_json({"type": "utterance", "text": "तुम क्या क्या कर सकती हो?"})
            capability, cap_state = take(ws, 1)
            assert "फ़ॉर्म" in capability
            assert "फिर से सुनना" not in capability
            assert cap_state["llm"] == "used"

            ws.send_json({"type": "utterance", "text": "मैं झारखंड के पाकड़ से हूँ।"})
            place, place_state = take(ws, 2)
            profile = place_state["profile"]
            assert profile["state"] == "JH"
            assert profile["state_name"] == "Jharkhand"
            assert profile["district"] is None
            assert "पाकुड़" in place
            assert "किस ज़िले और राज्य" not in place
            assert "झारखंड लिख लिया" in place
            assert place_state["llm"] == "used"

            ws.send_json({"type": "utterance", "text": "हाँ"})
            _yes, yes_state = take(ws, 3)
            assert yes_state["profile"]["district"] == "Pakur"
            assert yes_state["profile"]["state"] == "JH"

    assert model.seen[0] == "तुम क्या क्या कर सकती हो?"
    assert "पाकड़" in model.seen[1]
