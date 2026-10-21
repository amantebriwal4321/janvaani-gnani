"""Short answers have to land in the slot, danda and all.

The live failure was 'खेती।' after the occupation question. The danda stayed
on the word, and खेती was not in the matcher, so the fixed reprompt came back.
"""

import asyncio

from app.engine import Brain
from app.extract import answer_pending, extract, strip_slot_punct
from app.llm import LLMTurn, coerce_patch
from app.models import Profile


def _run(coro):
    return asyncio.run(coro)


def _ready(occupation_pending: bool = True) -> Brain:
    brain = Brain()
    brain.set_language("hi")
    brain.profile = Profile(district="Pakur", state="JH", state_name="Jharkhand")
    brain.pending = "occupation" if occupation_pending else None
    return brain


def test_punctuation_comes_off_without_eating_a_decimal():
    assert strip_slot_punct("खेती।") == "खेती"
    assert strip_slot_punct("  मज़दूरी ॥ ") == "मज़दूरी"
    assert strip_slot_punct("kheti.") == "kheti"
    assert strip_slot_punct("45,") == "45"
    assert strip_slot_punct("2.5।") == "2.5"
    assert strip_slot_punct("हाँ?") == "हाँ"


def test_kheti_with_danda_is_farming():
    found = extract("खेती।")
    assert found.values["occupation"] == "farmer"
    assert answer_pending("occupation", "खेती।") == "farmer"
    assert answer_pending("occupation", "किसान") == "farmer"
    assert answer_pending("occupation", "kheti.") == "farmer"
    assert answer_pending("occupation", "farming!") == "farmer"
    assert answer_pending("occupation", "farmer") == "farmer"
    assert answer_pending("occupation", "kisan") == "farmer"

    brain = _ready()

    async def run():
        result = await brain.utterance("खेती।", None)
        assert brain.profile.occupation == "farmer"
        assert "फिर से सुनना" not in result.reply
        assert "क्या काम करते" not in result.reply
        assert "ज़मीन" in result.reply or "एकड़" in result.reply

    _run(run())


def test_wage_work_and_shop_survive_punctuation():
    assert extract("मज़दूरी।").values["occupation"] == "labourer"
    assert extract("मजदूरी").values["occupation"] == "labourer"
    assert extract("mazdoori.").values["occupation"] == "labourer"
    assert extract("दुकान।").values["occupation"] == "street_vendor"
    assert extract("dukaan").values["occupation"] == "street_vendor"
    assert extract("a shop.").values["occupation"] == "street_vendor"

    brain = _ready()

    async def run():
        result = await brain.utterance("मज़दूरी।", None)
        assert brain.profile.occupation == "labourer"
        assert "फिर से सुनना" not in result.reply
        assert "क्या काम करते" not in result.reply

    _run(run())


def test_occupation_words_in_each_call_language():
    samples = {
        "ರೈತ.": "farmer",
        "రైతు.": "farmer",
        "விவசாயம்.": "farmer",
        "शेती।": "farmer",
        "চাষ।": "farmer",
        "കൃഷി.": "farmer",
        "ಕೂಲಿ.": "labourer",
        "కూలీ.": "labourer",
        "கூலி.": "labourer",
        "मजुरी।": "labourer",
        "মজুরি।": "labourer",
        "കൂലി.": "labourer",
        "ಅಂಗಡಿ.": "street_vendor",
        "దుకాణం.": "street_vendor",
        "கடை.": "street_vendor",
        "দোকান।": "street_vendor",
        "കട.": "street_vendor",
        "शिवण.": "artisan",
        "দর্জি.": "artisan",
    }
    for text, occupation in samples.items():
        assert extract(text).values["occupation"] == occupation, text


def test_other_slots_ignore_the_same_punctuation():
    assert answer_pending("age", "45।") == 45
    assert answer_pending("age", "पैंतालीस।") == 45
    assert answer_pending("land_acres", "2.5।") == 2.5
    assert answer_pending("land_acres", "दो।") == 2
    assert extract("दो एकड़।").values["land_acres"] == 2
    assert extract("गाँव।").values["area"] == "rural"
    assert extract("शहर।").values["area"] == "urban"
    assert answer_pending("bank_account", "हाँ।") is True
    assert answer_pending("bank_account", "नहीं।") is False
    assert extract("गेहूं।").values["crop"] == "wheat"
    assert extract("कच्चा।").values["housing"] == "kutcha"
    assert extract("पक्का।").values["housing"] == "pucca"
    assert extract("ओबीसी।").values["category"] == "obc"
    assert extract("सिलेंडर।").values["lpg"] is True

    brain = _ready(False)
    brain.profile.occupation = "farmer"
    brain.profile.land_acres = 2
    brain.pending = "age"

    async def run():
        result = await brain.utterance("45।", None)
        assert brain.profile.age == 45
        assert "फिर से सुनना" not in result.reply
        bank = Brain()
        bank.set_language("hi")
        bank.profile = Profile(
            district="Pakur",
            state="JH",
            state_name="Jharkhand",
            occupation="labourer",
            age=30,
        )
        bank.pending = "bank_account"
        await bank.utterance("हाँ।", None)
        assert bank.profile.bank_account is True

    _run(run())


def test_model_maps_kheti_and_extracts_the_slot_when_rules_miss():
    assert coerce_patch({"occupation": "खेती।"})["occupation"] == "farmer"
    assert coerce_patch({"occupation": "मज़दूरी"})["occupation"] == "labourer"
    assert coerce_patch({"crop": "गेहूं।"})["crop"] == "wheat"

    class _Model:
        def __init__(self) -> None:
            self.slot = None

        async def complete_turn(self, **kwargs) -> LLMTurn:
            return LLMTurn(fields={}, reply="ठीक है, लिख लिया।")

        async def extract_slot(self, **kwargs) -> dict:
            self.slot = kwargs["field"]
            return {"occupation": "खेती।"}

    brain = _ready()
    model = _Model()

    async def run():
        result = await brain.utterance("वही वाला काम।", model)
        assert model.slot == "occupation"
        assert brain.profile.occupation == "farmer"
        assert brain.llm_status == "used"
        assert "फिर से सुनना" not in result.reply
        assert "क्या काम करते" not in result.reply

    _run(run())


def test_an_unrelated_line_still_asks_again_without_a_model():
    brain = _ready()

    async def run():
        result = await brain.utterance("आज मौसम कैसा है?", None)
        assert brain.profile.occupation is None
        assert "काम" in result.reply

    _run(run())
