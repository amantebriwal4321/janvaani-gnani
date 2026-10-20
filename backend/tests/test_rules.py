"""Rule engine, extractor, slip, and the mock call socket."""

import json
import re

from fastapi.testclient import TestClient

from app.audio import linear_to_ulaw, mulaw_to_pcm16, pcm16_to_mulaw, ulaw_to_linear
from app.engine import Brain, echo_of_assistant, gaps_only
from app.extract import extract
from app.languages import BIAS_WORDS
from app.llm import coerce_patch
from app.main import app
from app.models import Profile
from app.schemes import CATALOG, match_all
from app.slip import build_pdf, slip_from_client
from app.telephony import exotel_inbound_pcm, twilio_inbound_pcm
import app.telephony as telephony

KOLAR = (
    "Main Kolar ke paas ek gaon se hoon, do acre mein tamatar ugata hoon, "
    "umar pentalees saal. Is baar baarish se fasal kharab ho gayi. "
    "BPL card hai, pitaji bahattar saal ke hain."
)
KAN = "ನಾನು ಮೈಸೂರಿನ ಹಳ್ಳಿಯಿಂದ. ನಾನು ದರ್ಜಿ. ವಯಸ್ಸು 38. ನಾನು ಹೆಂಗಸು."
TEL = "నేను నిజామాబాద్ రైతు. 3 ఎకరాలు. వయసు 50."
VENDOR = "Main Nagpur se hoon, thela lagata hoon, umar tees saal, mard hoon, BPL nahi hai, bank account nahi hai."


def _ids(profile: Profile, status: str) -> set[str]:
    return {item.scheme_id for item in match_all(profile) if item.status == status}


def test_bias_words_are_letters_only():
    assert BIAS_WORDS
    assert len(BIAS_WORDS) <= 100
    for word in BIAS_WORDS:
        assert re.fullmatch(r"[A-Za-z]+", word), word


def test_catalog_has_more_than_ten_schemes():
    assert len(CATALOG) >= 16
    assert len({scheme.id for scheme in CATALOG}) == len(CATALOG)


def test_kolar_farmer_extracts_the_household():
    found = extract(KOLAR)
    assert found.language == "hi-en"
    assert found.values["district"] == "Kolar"
    assert found.values["state"] == "KA"
    assert found.values["area"] == "rural"
    assert found.values["occupation"] == "farmer"
    assert found.values["land_acres"] == 2
    assert found.values["crop"] == "tomato"
    assert found.values["age"] == 45
    assert found.values["senior_age"] == 72
    assert found.values["bpl"] is True
    assert found.values["crop_loss"] is True
    assert found.ignored_id_number is False


def test_kolar_flow_reaches_a_ready_slip():
    brain = Brain()
    brain.set_language("hi")

    async def run():
        first = await brain.utterance(KOLAR, None)
        assert brain.language == "hi"
        assert "पीएम किसान" in first.reply
        assert brain.pending == "name_match"
        qualify = _ids(brain.profile, "qualify")
        assert {"pm_kisan", "pmfby", "pmjay", "vay_vandana", "mgnrega", "eshram", "ignoaps"} <= qualify
        assert first.snapshot["slip"] == "draft"

        await brain.utterance("nahi, naam alag likha hai", None)
        assert brain.profile.name_match is False
        assert brain.pending == "mobile_linked"

        await brain.utterance("haan", None)
        assert brain.profile.mobile_linked is True
        assert brain.pending == "bank_account"

        last = await brain.utterance("haan", None)
        assert brain.profile.bank_account is True
        assert last.snapshot["slip"] == "ready"
        assert any("name" in note.lower() for note in last.snapshot["fix_first"])
        assert "PM-KISAN" in last.snapshot["share_text"]
        assert not re.search(r"\d{10,}", last.snapshot["share_text"])
        pdf = build_pdf(brain)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1500

    import asyncio

    asyncio.run(run())


def test_kannada_tailor_gets_vishwakarma():
    found = extract(KAN)
    assert found.language == "kn"
    assert found.values["district"] == "Mysuru"
    assert found.values["state"] == "KA"
    assert found.values["area"] == "rural"
    assert found.values["occupation"] == "artisan"
    assert found.values["artisan_trade"] == "tailor"
    assert found.values["age"] == 38
    assert found.values["gender"] == "woman"
    profile = Profile(**found.values)
    qualify = _ids(profile, "qualify")
    assert "vishwakarma" in qualify
    assert "mgnrega" in qualify
    assert "eshram" in qualify


def test_telugu_farmer_gets_rythu_bharosa():
    found = extract(TEL)
    assert found.language == "te"
    assert found.values["district"] == "Nizamabad"
    assert found.values["state"] == "TG"
    assert found.values["occupation"] == "farmer"
    assert found.values["land_acres"] == 3
    assert found.values["age"] == 50
    assert "rythu_bharosa" in _ids(Profile(**found.values), "qualify")
    assert "pm_kisan" in _ids(Profile(**found.values), "qualify")


def test_nagpur_vendor_is_not_ladki_bahin():
    found = extract(VENDOR)
    assert found.values["district"] == "Nagpur"
    assert found.values["state"] == "MH"
    assert found.values["occupation"] == "street_vendor"
    assert found.values["age"] == 30
    assert found.values["gender"] == "man"
    assert found.values["bpl"] is False
    assert found.values["bank_account"] is False
    profile = Profile(**found.values)
    qualify = _ids(profile, "qualify")
    assert "svanidhi" in qualify
    assert "jandhan" in qualify
    assert "ladki_bahin" in _ids(profile, "not_eligible")


def test_salaried_city_household_is_not_a_farmer_scheme():
    profile = Profile(
        occupation="salaried",
        area="urban",
        state="DL",
        state_name="Delhi",
        age=35,
        gender="man",
        annual_income=800000,
        bpl=False,
        bank_account=True,
    )
    assert "pm_kisan" in _ids(profile, "not_eligible")
    assert "mgnrega" in _ids(profile, "not_eligible")
    assert "pmjay" in _ids(profile, "not_eligible")
    assert "vay_vandana" in _ids(profile, "not_eligible")


def test_farmer_without_land_needs_an_answer():
    profile = Profile(occupation="farmer", state="KA", state_name="Karnataka", area="rural", age=40)
    needs = [item for item in match_all(profile) if item.scheme_id == "pm_kisan"][0]
    assert needs.status == "need_answer"
    assert "land_acres" in needs.missing


def test_llm_cannot_overwrite_a_rule():
    profile = Profile(occupation="farmer", land_acres=2, age=45)
    patch = coerce_patch({"occupation": "salaried", "crop": "ragi", "age": 90, "aadhaar": "123412341234"})
    gaps = gaps_only(profile, patch)
    assert "occupation" not in gaps
    assert "age" not in gaps
    assert gaps["crop"] == "ragi"
    assert "aadhaar" not in patch


def test_id_number_is_not_stored():
    found = extract("My aadhaar is 123412341234 and I farm 2 acres in Kolar")
    assert found.ignored_id_number is True
    blob = json.dumps(found.values)
    assert "123412341234" not in blob
    assert found.values["occupation"] == "farmer"
    assert found.values["district"] == "Kolar"


def test_echo_filter_keeps_short_answers():
    assert echo_of_assistant("haan", "क्या आपका बैंक खाता है?") is False
    assert echo_of_assistant("The CSC slip is ready. Carry the papers", "The CSC slip is ready. Carry the papers for PM-Kisan.") is True


def test_mulaw_silence_and_roundtrip():
    assert linear_to_ulaw(0) == 0xFF
    assert abs(ulaw_to_linear(0xFF)) < 10
    pcm = b"\x00\x10\x00\x20\xff\x10\x00\x00"
    back = mulaw_to_pcm16(pcm16_to_mulaw(pcm))
    assert len(back) == len(pcm)


def test_twilio_and_exotel_frames():
    pcm = b"\x00\x00" * 160
    payload = telephony.base64.b64encode(pcm16_to_mulaw(pcm)).decode()
    decoded = twilio_inbound_pcm({"event": "media", "media": {"payload": payload}})
    assert decoded is not None and len(decoded) == 320

    loud = b"\xff\x7f" * 160  # not used
    exotel = exotel_inbound_pcm(
        {"event": "media", "media": {"payload": telephony.base64.b64encode(pcm).decode()}},
        8000,
    )
    assert exotel == pcm
    halved = exotel_inbound_pcm(
        {"event": "media", "media": {"payload": telephony.base64.b64encode(pcm + pcm).decode()}},
        16000,
    )
    assert len(halved) == len(pcm)
    assert loud  # keep the sample referenced


def test_mock_call_socket_end_to_end(monkeypatch):
    monkeypatch.setattr("app.config.settings.gnani_api_key", "")
    monkeypatch.setattr("app.config.settings.llm_base_url", "")
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["speech"] == "mock"
        assert health.json()["schemes"] >= 16
        with client.websocket_connect("/ws/call") as ws:
            ws.send_json({"type": "start", "language": "hi"})
            ready = _until(ws, lambda m: m.get("type") == "ready")
            session_id = ready["sessionId"]
            _until(ws, lambda m: m.get("type") == "speak")
            ws.send_json({"type": "utterance", "text": KOLAR})
            state = _until(ws, lambda m: m.get("type") == "state" and m["state"]["user_turns"] >= 1)
            assert state["state"]["slip"] == "draft"
            assert any(item["id"] == "pm_kisan" and item["status"] == "qualify" for item in state["state"]["matches"])
            for line in ("nahi, naam alag likha hai", "haan", "haan"):
                ws.send_json({"type": "utterance", "text": line})
                state = _until(ws, lambda m: m.get("type") == "state" and m["state"]["user_turns"] >= state["state"]["user_turns"] + 1)
            assert state["state"]["slip"] == "ready"
        pdf = client.get(f"/api/sessions/{session_id}/slip.pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        share = client.get(f"/api/sessions/{session_id}/share.txt")
        assert "PM-KISAN" in share.text
        assert "123412341234" not in share.text


def test_posted_slip_prints_without_the_call_and_drops_id_numbers():
    brain = Brain()
    snap = brain.snapshot()
    snap["rows"] = [{"label": "Note", "value": "123412341234", "heard": "said it"}]
    cleaned = slip_from_client(snap)
    assert "123412341234" not in json.dumps(cleaned)
    with TestClient(app) as client:
        response = client.post("/api/slip", json=snap)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert b"123412341234" not in response.content


def _until(ws, predicate, limit=30):
    last = None
    for _ in range(limit):
        message = ws.receive_json()
        last = message
        if predicate(message):
            return message
    raise AssertionError(last)
