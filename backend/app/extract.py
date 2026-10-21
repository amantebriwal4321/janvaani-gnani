"""Deterministic household extractor. Rules run on every turn, with or without an LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.translit import latin_words

# Native digits → ASCII so ages and acres survive Devanagari, Kannada, Telugu, Tamil, Bengali, Malayalam.
_DIGIT_SRC = "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯౦౧౨౩౪౫౬౭౮౯௦௧௨௩௪௫௬௭௮௯০১২৩৪৫৬৭৮৯൦൧൨൩൪൫൬൭൮൯"
_DIGIT_DST = "0123456789" * 6
DIGIT_TABLE = str.maketrans(_DIGIT_SRC, _DIGIT_DST)

NUMBER_WORDS: dict[str, int] = {
    "shunya": 0,
    "zero": 0,
    "ek": 1,
    "do": 2,
    "दो": 2,
    "teen": 3,
    "tin": 3,
    "तीन": 3,
    "char": 4,
    "chaar": 4,
    "चार": 4,
    "paanch": 5,
    "panch": 5,
    "पाँच": 5,
    "पांच": 5,
    "chhe": 6,
    "che": 6,
    "chhah": 6,
    "saat": 7,
    "सात": 7,
    "aath": 8,
    "ath": 8,
    "आठ": 8,
    "nau": 9,
    "नौ": 9,
    "das": 10,
    "दस": 10,
    "gyarah": 11,
    "gyara": 11,
    "barah": 12,
    "bara": 12,
    "terah": 13,
    "chaudah": 14,
    "pandrah": 15,
    "pandra": 15,
    "solah": 16,
    "satrah": 17,
    "atharah": 18,
    "unnis": 19,
    "bees": 20,
    "bis": 20,
    "बीस": 20,
    "ikkees": 21,
    "ikkis": 21,
    "baees": 22,
    "pachees": 25,
    "pachis": 25,
    "पच्चीस": 25,
    "tees": 30,
    "tis": 30,
    "तीस": 30,
    "chalis": 40,
    "chaalis": 40,
    "चालीस": 40,
    "paintalis": 45,
    "pentalis": 45,
    "pentalees": 45,
    "paintalees": 45,
    "pentaalees": 45,
    "पैंतालीस": 45,
    "pachas": 50,
    "pachaas": 50,
    "पचास": 50,
    "saath": 60,
    "sath": 60,
    "साठ": 60,
    "sattar": 70,
    "सत्तर": 70,
    "bahattar": 72,
    "bahatar": 72,
    "बहत्तर": 72,
    "assi": 80,
    "nabbe": 90,
    "sau": 100,
}

_NUM_ALT = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
NUM = rf"(?:(?<![a-z0-9])(?:{_NUM_ALT})(?![a-z])|\d+(?:\.\d+)?)"

LAND_UNITS = (
    r"acres?|ekar|ekaad|एकड़|एकर|ಎಕರೆ|ఎకరా|ఎకరాలు|ఎకరాల|ஏக்கர்|ഏക്കർ|একর"
)
AGE_UNITS = r"saal|sal|varsh|varsha|years?|ವರ್ಷ|ఏళ్లు|ఏళ్ళు|வயது|वर्षे|वर्ष|বছর|വയസ്|വയസ്സ്|साल"
AGE_CUES = r"umar|umra|umr|age|vayassu|vayasu|వయసు|వయస్సు|ವಯಸ್ಸು|வயது|उम्र|उमर|বয়স|പ്രായം|वय"

KIN = re.compile(
    r"pitaji|pitaaji|pita|papa|father|mataji|mummy|\bmaa\b|amma|mother|dadaji|dadi|pati\b|husband|wife|patni",
    re.I,
)
NEG = re.compile(
    r"nahi|nahin|\bno\b|\bnot\b|illa|ledu|illai|\balla\b|beda|ಕಾದು|ಇಲ್ಲ|ఇల్ల|అల్ల|இல்லை|ഇല്ല|না|नहीं|नाही",
    re.I,
)

LANG_SWITCH = (
    ("kn", ("kannada", "ಕನ್ನಡ")),
    ("te", ("telugu", "తెలుగు")),
    ("ta", ("tamil", "தமிழ்")),
    ("mr", ("marathi", "मराठी")),
    ("bn", ("bengali", "bangla", "বাংলা")),
    ("ml", ("malayalam", "മലയാളം")),
    ("hi-en", ("hinglish",)),
    ("hi", ("hindi", "हिन्दी", "हिंदी")),
    ("en", ("english",)),
)

STATES = {
    "KA": "Karnataka",
    "TG": "Telangana",
    "TN": "Tamil Nadu",
    "MH": "Maharashtra",
    "WB": "West Bengal",
    "KL": "Kerala",
    "AP": "Andhra Pradesh",
    "UP": "Uttar Pradesh",
    "BR": "Bihar",
    "RJ": "Rajasthan",
    "GJ": "Gujarat",
    "OD": "Odisha",
    "MP": "Madhya Pradesh",
    "AS": "Assam",
    "PB": "Punjab",
    "HR": "Haryana",
    "DL": "Delhi",
    "JH": "Jharkhand",
    "CT": "Chhattisgarh",
}

DISTRICTS: dict[str, tuple[str, str]] = {}


def _add_districts(state: str, names: list[str]) -> None:
    for name in names:
        DISTRICTS[name.lower()] = (name, state)


_add_districts(
    "KA",
    [
        "Kolar",
        "Mandya",
        "Mysuru",
        "Mysore",
        "Hassan",
        "Raichur",
        "Ballari",
        "Bidar",
        "Kalaburagi",
        "Gulbarga",
        "Tumakuru",
        "Tumkur",
        "Chitradurga",
        "Davangere",
        "Shivamogga",
        "Shimoga",
        "Vijayapura",
        "Bijapur",
        "Haveri",
        "Koppal",
        "Yadgir",
        "Chikkaballapura",
        "Ramanagara",
        "ಮೈಸೂರು",
        "ಕೋಲಾರ",
    ],
)
_add_districts(
    "TG",
    [
        "Nizamabad",
        "Karimnagar",
        "Warangal",
        "Khammam",
        "Adilabad",
        "Nalgonda",
        "Mahabubnagar",
        "Siddipet",
        "నిజామాబాద్",
    ],
)
_add_districts(
    "TN",
    [
        "Madurai",
        "Salem",
        "Thanjavur",
        "Tirunelveli",
        "Vellore",
        "Erode",
        "Dindigul",
        "Cuddalore",
        "Nagapattinam",
    ],
)
_add_districts(
    "MH",
    [
        "Nashik",
        "Kolhapur",
        "Solapur",
        "Sangli",
        "Satara",
        "Ahmednagar",
        "Nanded",
        "Latur",
        "Amravati",
        "Chandrapur",
        "Yavatmal",
        "Jalgaon",
        "Nagpur",
    ],
)
_add_districts(
    "WB",
    ["Malda", "Murshidabad", "Bankura", "Purulia", "Birbhum", "Jalpaiguri", "Nadia", "Medinipur"],
)
_add_districts("KL", ["Wayanad", "Idukki", "Palakkad", "Alappuzha", "Kannur", "Kasaragod", "Pathanamthitta"])
_add_districts("UP", ["Varanasi", "Gorakhpur", "Azamgarh", "Jaunpur"])
_add_districts("BR", ["Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga"])
_add_districts("RJ", ["Udaipur", "Ajmer", "Bikaner", "Kota"])
_add_districts("GJ", ["Rajkot", "Bhavnagar", "Junagadh"])
_add_districts("OD", ["Cuttack", "Berhampur", "Sambalpur"])
_add_districts("MP", ["Indore", "Ujjain", "Satna", "Rewa"])
_add_districts("AS", ["Dibrugarh", "Silchar"])
_add_districts(
    "JH",
    [
        "Pakur",
        "Ranchi",
        "Dhanbad",
        "Bokaro",
        "Dumka",
        "Deoghar",
        "Jamtara",
        "Godda",
        "Sahebganj",
        "Giridih",
        "Hazaribagh",
        "Jamshedpur",
        "Chatra",
        "Koderma",
        "Ramgarh",
        "Palamu",
        "Garhwa",
        "Latehar",
        "Lohardaga",
        "Gumla",
        "Simdega",
        "Khunti",
        "Chaibasa",
    ],
)

# Spoken aliases and native-script names display in portal English on the slip.
DISTRICTS["mysore"] = ("Mysuru", "KA")
DISTRICTS["mysuru"] = ("Mysuru", "KA")
DISTRICTS["ಮೈಸೂರು"] = ("Mysuru", "KA")
DISTRICTS["ಮೈಸೂರ"] = ("Mysuru", "KA")
DISTRICTS["ಕೋಲಾರ"] = ("Kolar", "KA")
DISTRICTS["నిజామాబాద్"] = ("Nizamabad", "TG")
DISTRICTS["पाकुड़"] = ("Pakur", "JH")
DISTRICTS["পাকুড়"] = ("Pakur", "JH")
DISTRICTS["बाँकुड़ा"] = ("Bankura", "WB")
DISTRICTS["বাঁকুড়া"] = ("Bankura", "WB")

STATE_WORDS = {
    "karnataka": "KA",
    "कर्नाटक": "KA",
    "ಕರ್ನಾಟಕ": "KA",
    "telangana": "TG",
    "తెలంగాణ": "TG",
    "tamil nadu": "TN",
    "tamilnadu": "TN",
    "தமிழ்நாடு": "TN",
    "maharashtra": "MH",
    "महाराष्ट्र": "MH",
    "west bengal": "WB",
    "bengal": "WB",
    "পশ্চিমবঙ্গ": "WB",
    "kerala": "KL",
    "കേരളം": "KL",
    "andhra": "AP",
    "uttar pradesh": "UP",
    "bihar": "BR",
    "rajasthan": "RJ",
    "gujarat": "GJ",
    "odisha": "OD",
    "orissa": "OD",
    "madhya pradesh": "MP",
    "assam": "AS",
    "punjab": "PB",
    "haryana": "HR",
    "delhi": "DL",
    "jharkhand": "JH",
    "jharakhand": "JH",
    "झारखंड": "JH",
    "झारखण्ड": "JH",
    "chhattisgarh": "CT",
    "छत्तीसगढ़": "CT",
    "बिहार": "BR",
    "राजस्थान": "RJ",
    "गुजरात": "GJ",
    "ओडिशा": "OD",
    "पंजाब": "PB",
    "हरियाणा": "HR",
    "दिल्ली": "DL",
    "असम": "AS",
    "केरल": "KL",
    "ঝাড়খণ্ড": "JH",
    "পশ্চিমবঙ্গ": "WB",
}

OCCUPATIONS = (
    (
        "street_vendor",
        (
            "street vendor",
            "thela",
            "thela lagata",
            "pheriwala",
            "hawker",
            "rehri",
            "dukaan",
            "dukan",
            "shop",
            "दुकान",
            "दूकान",
            "ठेला",
            "फेरी",
            "रेहड़ी",
            "ಅಂಗಡಿ",
            "దుకాణం",
            "கடை",
            "দোকান",
            "കട",
        ),
    ),
    (
        "artisan",
        (
            "darzi",
            "tailor",
            "carpenter",
            "badhai",
            "lohar",
            "kumhar",
            "mochi",
            "barber",
            "julaha",
            "weaver",
            "sonar",
            "goldsmith",
            "rajmistri",
            "blacksmith",
            "potter",
            "कारीगर",
            "दर्जी",
            "लोहार",
            "कुम्हार",
            "शिवण",
            "ದರ್ಜಿ",
            "దర్జీ",
            "தையல்",
            "দর্জি",
            "തയ്യൽ",
        ),
    ),
    (
        "farmer",
        (
            "kisan",
            "kheti",
            "khet",
            "krishi",
            "farming",
            "farmer",
            "farm",
            "agriculture",
            "ugata",
            "ugate",
            "ugati",
            "rythu",
            "raithu",
            "raitu",
            "vivasayi",
            "shetkari",
            "chashi",
            "खेती",
            "खेतीबाड़ी",
            "खेत",
            "किसान",
            "कृषक",
            "कृषि",
            "शेती",
            "शेतकरी",
            "शेत",
            "ರೈತ",
            "ಕೃಷಿ",
            "రైతు",
            "వ్యవసాయం",
            "సాగు",
            "விவசாயம்",
            "விவசாயி",
            "உழவு",
            "চাষ",
            "চাষি",
            "কৃষি",
            "কৃষক",
            "കൃഷി",
            "കർഷകൻ",
            "കർഷക",
        ),
    ),
    (
        "labourer",
        (
            "mazdoori",
            "mazdoor",
            "majdoor",
            "majdoori",
            "mazdur",
            "labourer",
            "labour",
            "laborer",
            "labor",
            "coolie",
            "daily wage",
            "wage work",
            "kooli",
            "dihadi",
            "मजदूरी",
            "मज़दूरी",
            "मजदूर",
            "मज़दूर",
            "दिहाड़ी",
            "मजुरी",
            "मजूर",
            "मजूरी",
            "ಕೂಲಿ",
            "కూలీ",
            "కూలి",
            "கூலி",
            "মজুরি",
            "মজুর",
            "കൂലി",
            "കൂലിപ്പണി",
        ),
    ),
    ("homemaker", ("homemaker", "housewife", "grihini", "गृहिणी", "घरवाली", "ಮನೆಕೆಲಸ", "ఇంటి పని", "வீட்டு வேலை", "घरकाम", "গৃহিণী", "വീട്ടമ്മ")),
    ("student", ("student", "padhai", "college", "विद्यार्थी", "छात्र", "पढ़ाई", "ವಿದ್ಯಾರ್ಥಿ", "విద్యార్థి", "மாணவர்", "ছাত্র", "വിദ്യാർത്ഥി")),
    (
        "salaried",
        (
            "naukri",
            "salary",
            "office job",
            "private job",
            "government job",
            "नौकरी",
            "वेतन",
            "ನೌಕರಿ",
            "ఉద్యోగం",
            "జీతం",
            "சம்பளம்",
            "नोकरी",
            "চাকরি",
            "ശമ്പളം",
        ),
    ),
)

TRADES = (
    ("tailor", ("darzi", "tailor", "ದರ್ಜಿ", "దర్జీ", "தையல்")),
    ("carpenter", ("carpenter", "badhai")),
    ("blacksmith", ("lohar", "blacksmith")),
    ("potter", ("kumhar", "potter")),
    ("cobbler", ("mochi", "cobbler")),
    ("barber", ("barber", "hajam")),
    ("weaver", ("weaver", "julaha", "bunkar")),
    ("goldsmith", ("sonar", "goldsmith")),
    ("mason", ("mason", "rajmistri")),
)

CROPS = (
    ("tomato", ("tamatar", "tomato", "टमाटर", "ಟೊಮೇಟೊ", "టమాట", "தக்காளி", "টমেটো")),
    ("wheat", ("gehun", "gehun", "wheat", "godhuma", "गेहूं", "गेहूँ", "गहू", "ಗೋಧಿ", "గోధుమ", "கோதுமை", "গম", "ഗോതമ്പ്")),
    ("rice", ("dhan", "rice", "paddy", "bhatta", "nellu", "धान", "चावल", "भात", "ಭತ್ತ", "వరి", "நெல்", "ধান", "അരി")),
    ("cotton", ("kapas", "cotton", "कपास", "ಕಾಪಾಸು", "పత్తి", "பருத்தி", "তুলো")),
    ("ragi", ("ragi", "raagi", "रागी", "नाचनी", "রাগি")),
    ("jowar", ("jowar", "sorghum", "ज्वार", "ज्वारी")),
    ("tur", ("tur dal", "tur", "अरहर", "तूर")),
    ("onion", ("pyaz", "onion", "ullagadda", "प्याज", "कांदा")),
    ("chilli", ("mirchi", "chilli", "chili", "मिर्च", "मिर्ची")),
    ("maize", ("makka", "maize", "corn", "मक्का", "मक्की")),
    ("sugarcane", ("ganna", "sugarcane", "गन्ना", "ऊस")),
    ("soyabean", ("soyabean", "soybean", "सोयाबीन")),
)

RURAL = (
    "gaon",
    "gaav",
    "village",
    "halli",
    "ಹಳ್ಳಿ",
    "గ్రామ",
    "గ్రామం",
    "கிராம",
    "கிராமம்",
    "গ্রাম",
    "ഗ്രാമ",
    "ഗ്രാമം",
    "गाव",
    "गाँव",
    "गांव",
    "ग्राम",
)
URBAN = (
    "shehar",
    "shahar",
    "city",
    "town",
    "urban",
    "nagarpalika",
    "शहर",
    "शहरी",
    "ನಗರ",
    "పట్టణం",
    "నగరం",
    "நகரம்",
    "শহর",
    "നഗരം",
)

WOMAN = (
    "aurat",
    "mahila",
    "woman",
    "female",
    "hengasu",
    "ಹೆಂಗಸು",
    "స్త్రీ",
    "మహిళ",
    "பெண்",
    "മഹിള",
    "महिला",
    "स्त्री",
    "মহিলা",
    "নারী",
    "ladki",
    "sthree",
)
MAN = ("aadmi", "admi", "purush", "mard", "male", "ಗಂಡಸು", "పురుషు", "ஆண்", "पुरुष", "आदमी")


@dataclass
class Extraction:
    values: dict
    heard: dict
    language: str | None
    ignored_id_number: bool
    switched_to: str | None
    guesses: dict | None = None


_PLACE_STOP = {
    "main",
    "mein",
    "me",
    "ke",
    "ki",
    "ka",
    "se",
    "hun",
    "hoon",
    "ho",
    "hu",
    "hai",
    "jo",
    "aur",
    "and",
    "the",
    "from",
    "am",
    "is",
    "my",
    "rajy",
    "rajya",
    "state",
    "district",
    "zila",
    "jila",
    "jela",
    "wala",
    "wali",
    "haan",
    "han",
    "nahi",
    "nahin",
    "yeah",
    "yep",
    "nope",
    "yes",
    "pakka",
    "pucca",
    "kutcha",
    "kachcha",
    "kaccha",
    "ghar",
    "house",
    "saal",
    "umar",
    "acre",
    "ekar",
}


def _fold_latin(word: str) -> str:
    return re.sub(r"[^a-z]", "", word.lower())


def _skeleton(word: str) -> str:
    return re.sub(r"[aeiou]", "", _fold_latin(word))


def _lev(left: str, right: str) -> int:
    if abs(len(left) - len(right)) > 2:
        return 9
    prev = list(range(len(right) + 1))
    for i, ca in enumerate(left, 1):
        cur = [i]
        for j, cb in enumerate(right, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _state_indexes() -> tuple[dict[str, str], dict[str, str]]:
    exact: dict[str, str] = {}
    for word, code in STATE_WORDS.items():
        if re.search(r"[a-z]", word):
            exact[_fold_latin(word)] = code
    for code, name in STATES.items():
        exact[_fold_latin(name)] = code
    skeletons: dict[str, str] = {}
    buckets: dict[str, set[str]] = {}
    for word, code in exact.items():
        buckets.setdefault(_skeleton(word), set()).add(code)
    for skel, codes in buckets.items():
        if len(codes) == 1 and len(skel) >= 4:
            skeletons[skel] = next(iter(codes))
    return exact, skeletons


_STATE_EXACT, _STATE_SKEL = _state_indexes()
_DISTRICT_FOLD: dict[str, tuple[str, str]] = {}
for _key, (_label, _state) in DISTRICTS.items():
    if re.search(r"[a-z]", _key):
        _DISTRICT_FOLD[_fold_latin(_key)] = (_label, _state)


def _script_state(text: str) -> str | None:
    for word, code in sorted(STATE_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(r"[a-z]", word):
            continue
        if word in text:
            return code
    return None


def _state_from_words(words: list[str]) -> str | None:
    for word in words:
        if word in _STATE_EXACT:
            return _STATE_EXACT[word]
        code = _STATE_SKEL.get(_skeleton(word))
        if code and len(word) >= 5:
            return code
    return None


def _script_district(text: str) -> tuple[str, str] | None:
    for key, (label, state) in sorted(DISTRICTS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(r"[a-z]", key):
            continue
        if key in text:
            return label, state
    return None


def _fuzzy_district(token: str, state: str | None, limit: int) -> tuple[str, str] | None:
    best: list[tuple[int, str, str]] = []
    for fold, (label, st) in _DISTRICT_FOLD.items():
        if state and st != state:
            continue
        dist = _lev(token, fold)
        if dist <= limit:
            best.append((dist, label, st))
    if not best:
        return None
    best.sort()
    top = best[0][0]
    labels = {label for dist, label, _st in best if dist == top}
    if len(labels) != 1 or top == 0:
        return None
    return best[0][1], best[0][2]


def resolve_place(original: str) -> tuple[dict, dict, dict]:
    """Certain place fields, the heard snippet, and a district that still needs a yes.

    An explicit state is kept even when the district belongs to another state.
    A fuzzy district is only a guess: it does not fill the profile.
    """
    words = [word for word in latin_words(original) if word not in _PLACE_STOP]
    state = _script_state(original) or _state_from_words(words)
    values: dict = {}
    heard: dict = {}
    guesses: dict = {}
    exact = _script_district(original)
    if exact is None:
        for word in words:
            hit = _DISTRICT_FOLD.get(word)
            if hit:
                exact = hit
                heard["district"] = word
                break
    if exact:
        label, home = exact
        values["district"] = label
        heard.setdefault("district", label)
        if state is None:
            state = home
    else:
        limit = 2 if state else 1
        for word in words:
            if len(word) < 4 or _skeleton(word) in _STATE_SKEL:
                continue
            hit = _fuzzy_district(word, state, limit)
            if hit:
                guesses["district"] = hit[0]
                guesses["district_state"] = hit[1]
                heard["district"] = word
                break
    if state:
        values["state"] = state
        values["state_name"] = STATES[state]
        heard.setdefault("state_name", STATES[state])
    return values, heard, guesses


def canonical_state(token: str) -> str | None:
    raw = (token or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in STATES:
        return upper
    script = _script_state(raw)
    if script:
        return script
    folded = _fold_latin(to_latin_token(raw))
    if folded in _STATE_EXACT:
        return _STATE_EXACT[folded]
    for word in latin_words(raw):
        if word in _STATE_EXACT:
            return _STATE_EXACT[word]
        code = _STATE_SKEL.get(_skeleton(word))
        if code and len(word) >= 5:
            return code
    return None


def classify_place_token(token: str, state: str | None = None) -> tuple[str, str, str] | None:
    """`exact` or `guess`, plus the district label and its home state code."""
    pieces = [word for word in latin_words(token) if word not in _PLACE_STOP]
    if not pieces:
        folded = _fold_latin(to_latin_token(token))
        pieces = [folded] if folded else []
    for piece in pieces:
        hit = _DISTRICT_FOLD.get(piece)
        if hit:
            return "exact", hit[0], hit[1]
    limit = 2 if state else 1
    for piece in pieces:
        if len(piece) < 4 or _skeleton(piece) in _STATE_SKEL:
            continue
        fuzzy = _fuzzy_district(piece, state, limit)
        if fuzzy:
            return "guess", fuzzy[0], fuzzy[1]
    return None


def to_latin_token(token: str) -> str:
    from app.translit import to_latin

    return to_latin(token)


_CAN_DO = re.compile(
    r"क्या\s*क्या\s*कर|क्या\s*कर\s*सक|what can you|kya\s+kya\s+kar|kya\s+kar\s+sak|"
    r"কি\s*করতে\s*পার|কী\s*করতে\s*পার",
    re.I,
)
_YES = {
    "हाँ",
    "हां",
    "हा",
    "जी",
    "ठीक",
    "सही",
    "yes",
    "yeah",
    "yep",
    "haan",
    "han",
    "ha",
    "houdu",
    "haudu",
    "avunu",
    "aama",
    "aam",
    "হ্যাঁ",
    "হ্যা",
    "আজ্ঞে",
    "हो",
    "होय",
    "ಹೌದು",
    "అవును",
    "ஆம்",
    "അതെ",
}
_NO = {
    "नहीं",
    "नही",
    "ना",
    "no",
    "nahi",
    "nahin",
    "না",
    "নাহ",
    "नाही",
    "इल्ला",
    "इल्ल",
    "ಇಲ್ಲ",
    "కాదు",
    "లేదు",
    "இல்லை",
    "ഇല്ല",
    "नाही",
}


def asks_capability(text: str) -> bool:
    return _CAN_DO.search(text or "") is not None


def yes_no(text: str) -> bool | None:
    token = strip_slot_punct(text)
    if not token or len(token.split()) > 3:
        return None
    if token in _YES or token.lower() in _YES:
        return True
    if token in _NO or token.lower() in _NO:
        return False
    return None


def normalize_digits(text: str) -> str:
    return text.translate(DIGIT_TABLE)


# Keep a decimal point between digits. Every other mark is noise around a slot answer,
# including the Hindi danda in "खेती।".
_SLOT_PUNCT = re.compile(
    r"(?<!\d)\.(?!\d)|[।॥॰!?？！,،؛;:：'\"“”‘’`´()\[\]{}<>…·•|/\\*_~@#%&+=^«»‐‑‒–—―]"
)


def _fold_nukta(text: str) -> str:
    return text.replace("़", "").replace("়", "")


def strip_slot_punct(text: str) -> str:
    """Punctuation and extra space come off before any slot is matched."""
    cleaned = (text or "").replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    cleaned = _SLOT_PUNCT.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_number(token: str) -> float | None:
    token = token.strip().lower()
    if not token:
        return None
    if token in NUMBER_WORDS:
        return float(NUMBER_WORDS[token])
    try:
        return float(token)
    except ValueError:
        return None


def _snippet(text: str, start: int, end: int) -> str:
    return text[start:end].strip()


def _negated(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 14) : min(len(text), end + 18)]
    return NEG.search(window) is not None


def _find_keyword(text: str, groups: tuple[tuple[str, tuple[str, ...]], ...]) -> tuple[str, str, int] | None:
    hay = _fold_nukta(strip_slot_punct(text))
    best: tuple[str, str, int] | None = None
    for label, words in groups:
        for word in words:
            needle = _fold_nukta(word.strip())
            if not needle:
                continue
            if re.search(r"[a-z]", needle):
                match = re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", hay, re.I)
                index = match.start() if match else -1
                found = needle
            else:
                index = hay.find(needle)
                found = needle
            if index != -1 and (best is None or index < best[2]):
                best = (label, found, index)
    return best


def detect_language(text: str) -> str | None:
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "ml"
    if re.search(r"[\u0900-\u097F]", text):
        if re.search(r"आहे|नाही|शेत|तुम्ही|होय", text):
            return "mr"
        return "hi"
    hinglish = re.search(
        r"\b(main|hoon|hun|hai|mera|meri|kisan|gaon|umar|nahi|haan|mein|wala|wali|bhai|rupaye|kaam)\b",
        text,
        re.I,
    )
    english = re.search(r"\b(the|is|are|my|from|years|farmer|have|has|what|with|and)\b", text, re.I)
    if hinglish:
        return "hi-en"
    if english:
        return "en"
    return None


def detect_switch(text: str) -> str | None:
    lowered = text.lower()
    for code, words in LANG_SWITCH:
        for word in words:
            if re.search(r"[a-z]", word):
                if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", lowered):
                    return code
            elif word in text:
                return code
    return None


def _polarity_word(text: str) -> bool | None:
    """True/False when the utterance is only a yes or a no, not a new fact."""
    cleaned = strip_slot_punct(text)
    if _find_keyword(cleaned, OCCUPATIONS) or re.search(NUM, cleaned, re.I):
        # A bare "do" is the number 2 and also not a yes. Facts win.
        if not re.fullmatch(r"(haan+|han|ha|yes|yeah|yep|no|nahi|nahin|nope)", cleaned, re.I):
            if re.search(r"\b(haan+|han|yes|yeah)\b", cleaned, re.I) and len(cleaned.split()) <= 2:
                return True
            return None
    answer = yes_no(cleaned)
    if answer is not None:
        return answer
    if re.search(r"\b(haan+|han|ha|yes|yeah|yep|houdu|haudu|avunu|aama|aam|ho|ji|sahi|correct)\b", cleaned, re.I):
        if not NEG.search(cleaned):
            return True
    if NEG.search(cleaned) and len(cleaned.split()) <= 6:
        return False
    return None


def polarity_for(field: str | None, text: str) -> bool | None:
    if not field:
        return None
    lowered = text.lower()
    if field == "name_match":
        if re.search(r"alag|mismatch|different|galat|ಬೇರೆ|వేరు|வேறு|আলাদা", lowered) or re.search(r"अलग", text):
            return False
        if re.search(r"ek jaisa|same name|naam same|barabar|match", lowered) or re.search(r"एक जैसा|एक जैसा", text):
            return True
    pure = _polarity_word(text)
    if pure is not None and field in {
        "bpl",
        "crop_loss",
        "widow",
        "disability",
        "pregnant",
        "bank_account",
        "aadhaar_seeded",
        "mobile_linked",
        "name_match",
        "lpg",
    }:
        return pure
    return None


_BARE_MEASURE = re.compile(rf"^({NUM})(?:\s+(?:{LAND_UNITS}|{AGE_UNITS}|lakh))?$", re.I)


def _bare_measure(field: str, text: str):
    """A reply that is only a number, optionally with a unit, for the slot just asked."""
    cleaned = _fold_nukta(strip_slot_punct(normalize_digits(text)))
    match = _BARE_MEASURE.match(cleaned)
    if not match:
        return None
    amount = _parse_number(match.group(1))
    if amount is None:
        return None
    if field == "annual_income":
        if re.search(r"lakh", cleaned, re.I):
            return int(amount * 100000)
        if amount >= 1000:
            return int(amount)
        return None
    if field == "land_acres":
        if 0 < amount <= 100:
            return float(amount)
        return None
    if field in ("age", "senior_age"):
        years = int(amount)
        if 1 <= years <= 120:
            return years
    return None


def answer_pending(field: str | None, text: str):
    """What a short reply means when this slot was the question just asked."""
    if not field:
        return None
    cleaned = strip_slot_punct(normalize_digits(text or ""))
    if not cleaned:
        return None
    if field == "occupation":
        hit = _find_keyword(cleaned, OCCUPATIONS)
        return hit[0] if hit else None
    if field == "artisan_trade":
        hit = _find_keyword(cleaned, TRADES)
        return hit[0] if hit else None
    if field == "crop":
        hit = _find_keyword(cleaned, CROPS)
        return hit[0] if hit else None
    if field == "gender":
        woman = _find_keyword(cleaned, (("woman", WOMAN),))
        man = _find_keyword(cleaned, (("man", MAN),))
        if woman and (not man or woman[2] <= man[2]):
            return "woman"
        if man:
            return "man"
        return None
    if field == "area":
        rural = _find_keyword(cleaned, (("rural", RURAL),))
        urban = _find_keyword(cleaned, (("urban", URBAN),))
        if rural and (not urban or rural[2] <= urban[2]):
            return "rural"
        if urban:
            return "urban"
        return None
    if field in ("age", "senior_age", "land_acres", "annual_income"):
        return _bare_measure(field, cleaned)
    if field in {
        "bpl",
        "crop_loss",
        "widow",
        "disability",
        "pregnant",
        "bank_account",
        "aadhaar_seeded",
        "mobile_linked",
        "name_match",
        "lpg",
    }:
        return polarity_for(field, cleaned)
    found = extract(cleaned)
    if field in found.values:
        return found.values[field]
    return None


def classify_enum(field: str, raw: str):
    """Map a model's own word, including 'खेती।', onto the profile value."""
    cleaned = strip_slot_punct(str(raw or ""))
    if not cleaned:
        return None
    if field in {"occupation", "crop", "artisan_trade", "gender", "area"}:
        return answer_pending(field, cleaned)
    found = extract(cleaned)
    if field in found.values:
        return found.values[field]
    return answer_pending(field, cleaned)


def extract(raw: str) -> Extraction:
    original = raw.strip()
    text = strip_slot_punct(normalize_digits(original))
    ignored = bool(re.search(r"\d{10,}", text))
    if ignored:
        text = re.sub(r"\d{10,}", " ", text)
    values: dict = {}
    heard: dict = {}

    def put(field: str, value, start: int, end: int) -> None:
        if value is None:
            return
        values[field] = value
        heard[field] = _snippet(text, start, end) or original[:80]

    # Place. Exact names fill the field. A near miss is only a guess.
    place_values, place_heard, place_guesses = resolve_place(text)
    for field, value in place_values.items():
        values[field] = value
        heard[field] = place_heard.get(field) or original[:80]

    for word in RURAL:
        if re.search(r"[a-z]", word):
            match = re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text, re.I)
            if match:
                put("area", "rural", match.start(), match.end())
                break
        elif word in text:
            index = text.find(word)
            put("area", "rural", index, index + len(word))
            break
    if "area" not in values:
        for word in URBAN:
            match = re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text, re.I)
            if match:
                put("area", "urban", match.start(), match.end())
                break

    occ = _find_keyword(text, OCCUPATIONS)
    if occ:
        put("occupation", occ[0], occ[2], occ[2] + len(occ[1]))
    trade = _find_keyword(text, TRADES)
    if trade:
        put("artisan_trade", trade[0], trade[2], trade[2] + len(trade[1]))
        if values.get("occupation") in (None, "artisan"):
            values["occupation"] = "artisan"
            heard.setdefault("occupation", heard.get("artisan_trade", trade[1]))

    crop = _find_keyword(text, CROPS)
    if crop:
        put("crop", crop[0], crop[2], crop[2] + len(crop[1]))
        if "occupation" not in values:
            values["occupation"] = "farmer"
            heard["occupation"] = heard["crop"]

    land = re.search(rf"({NUM})\s*(?:{LAND_UNITS})", text, re.I)
    if land:
        amount = _parse_number(land.group(1))
        if amount is not None:
            put("land_acres", amount, land.start(), land.end())

    income = re.search(rf"({NUM})\s*lakh", text, re.I)
    if income:
        amount = _parse_number(income.group(1))
        if amount is not None:
            values["annual_income"] = int(amount * 100000)
            heard["annual_income"] = _snippet(text, income.start(), income.end())

    # Age of the caller versus an elder mentioned beside the number.
    age_patterns = [
        re.compile(rf"(?:{AGE_CUES})\s*[:\-]?\s*({NUM})", re.I),
        re.compile(rf"({NUM})\s*(?:{AGE_UNITS})", re.I),
    ]
    for pattern in age_patterns:
        for match in pattern.finditer(text):
            number = _parse_number(match.group(1))
            if number is None:
                continue
            years = int(number)
            if years < 1 or years > 120:
                continue
            window = text[max(0, match.start() - 28) : match.start()]
            field = "senior_age" if KIN.search(window) else "age"
            if field in values and field != "senior_age":
                continue
            if field == "age" and "age" in values:
                continue
            put(field, years, match.start(), match.end())

    loss = re.search(r"kharab|nuksan|barbad|damage|naash|ನಷ್ಟ|నష్ట|நஷ்ட|ক্ষতি", text, re.I)
    if loss and not _negated(text, loss.start(), loss.end()):
        put("crop_loss", True, loss.start(), loss.end())

    bpl = re.search(r"\bbpl\b|बीपीएल|below poverty", text, re.I)
    if bpl:
        put("bpl", not _negated(text, bpl.start(), bpl.end()), bpl.start(), bpl.end())

    if re.search(r"antyodaya|\baay\b", text, re.I):
        match = re.search(r"antyodaya|\baay\b", text, re.I)
        assert match
        put("ration", "aay", match.start(), match.end())
        values["bpl"] = True
        heard.setdefault("bpl", heard["ration"])
    elif re.search(r"\bphh\b|priority household", text, re.I):
        match = re.search(r"\bphh\b|priority household", text, re.I)
        assert match
        put("ration", "phh", match.start(), match.end())
    elif re.search(r"ration|\braशन\b|राशन", text, re.I):
        match = re.search(r"ration|राशन", text, re.I)
        if match and not _negated(text, match.start(), match.end()):
            put("ration", "phh", match.start(), match.end())

    woman = _find_keyword(text, (("woman", WOMAN),))
    man = _find_keyword(text, (("man", MAN),))
    if woman and (not man or woman[2] <= man[2]):
        put("gender", "woman", woman[2], woman[2] + len(woman[1]))
    elif man:
        put("gender", "man", man[2], man[2] + len(man[1]))

    for field, pattern in (
        ("widow", r"widow|vidhwa|ವಿಧವೆ|వితంతు|விதவை|विधवा|বিধবা"),
        ("pregnant", r"pregnan|garbh|గర్భ|கர்ப்ப|गर्भ|গর্ভ"),
        ("disability", r"disability|divyang|viklang|వికల|மாற்றுத்திறன்|दिव्यांग"),
    ):
        match = re.search(pattern, text, re.I)
        if match:
            put(field, not _negated(text, match.start(), match.end()), match.start(), match.end())

    housing = re.search(r"kutcha|kachcha|kaccha|कच्चा|कच्चे|ಕಚ್ಚಾ|కచ్చా|கச்சா|কাঁচা|കച്ച", text, re.I)
    if housing:
        put("housing", "kutcha", housing.start(), housing.end())
    else:
        pucca = re.search(r"pucca|pakka|पक्का|पक्के|ಪಕ್ಕಾ|పక్కా|பக்கா|পাকা|പക്ക", text, re.I)
        if pucca and not _negated(text, pucca.start(), pucca.end()):
            put("housing", "pucca", pucca.start(), pucca.end())
    homeless = re.search(r"homeless|beghar|बेघर", text, re.I)
    if homeless:
        put("housing", "homeless", homeless.start(), homeless.end())

    lpg = re.search(
        r"\blpg\b|cylinder|gas connection|gas chulha|सिलेंडर|सिलिंडर|गैस|గ్యాస్|ಗ್ಯಾಸ್|கேஸ்|গ্যাস|ഗ്യാസ്",
        text,
        re.I,
    )
    if lpg:
        put("lpg", not _negated(text, lpg.start(), lpg.end()), lpg.start(), lpg.end())

    bank = re.search(r"bank(?:\s+account|\s+khata)?", text, re.I)
    if bank:
        put("bank_account", not _negated(text, bank.start(), bank.end()), bank.start(), bank.end())

    if re.search(r"seed", text, re.I) and re.search(r"aadhaar|aadhar|bank", text, re.I):
        match = re.search(r"seed", text, re.I)
        assert match
        put("aadhaar_seeded", not _negated(text, match.start(), match.end()), match.start(), match.end())

    if re.search(r"alag|mismatch|अलग", text, re.I):
        match = re.search(r"alag|mismatch|अलग", text, re.I)
        assert match
        put("name_match", False, match.start(), match.end())
    elif re.search(r"ek jaisa|same name|एक जैसा", text, re.I):
        match = re.search(r"ek jaisa|same name|एक जैसा", text, re.I)
        assert match
        put("name_match", True, match.start(), match.end())

    mobile = re.search(r"(mobile|phone).{0,20}(link|juda|aadhaar|aadhar)|(aadhaar|aadhar).{0,20}(mobile|phone)", text, re.I)
    if mobile:
        put("mobile_linked", not _negated(text, mobile.start(), mobile.end()), mobile.start(), mobile.end())

    category = re.search(
        r"scheduled tribe|\bst\b|अनुसूचित जनजाति|एसटी|scheduled caste|anusuchit|\bsc\b|अनुसूचित जाति|एससी|\bobc\b|ओबीसी|पिछड़",
        text,
        re.I,
    )
    if category:
        token = category.group(0).lower()
        if "tribe" in token or token == "st" or "जनजाति" in category.group(0) or "एसटी" in category.group(0):
            put("category", "st", category.start(), category.end())
        elif "caste" in token or token == "sc" or "anusuchit" in token or "जाति" in category.group(0) or "एससी" in category.group(0):
            put("category", "sc", category.start(), category.end())
        else:
            put("category", "obc", category.start(), category.end())

    return Extraction(
        values=values,
        heard=heard,
        language=detect_language(original),
        ignored_id_number=ignored,
        switched_to=detect_switch(original),
        guesses=place_guesses or None,
    )
