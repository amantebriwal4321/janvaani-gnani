"""Deterministic welfare rules. The LLM never sets a verdict."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Profile


def _names(hi: str, en: str, kn: str, te: str, ta: str, mr: str, bn: str, ml: str) -> dict[str, str]:
    return {
        "hi": hi,
        "hi-en": en,
        "en": en,
        "kn": kn,
        "te": te,
        "ta": ta,
        "mr": mr,
        "bn": bn,
        "ml": ml,
    }


@dataclass(frozen=True)
class Verdict:
    status: str  # qualify | likely | need_answer | not_eligible | insufficient
    reasons: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()


def qualify(*reasons: str) -> Verdict:
    return Verdict("qualify", reasons)


def likely(*reasons: str) -> Verdict:
    return Verdict("likely", reasons)


def need(*missing: str, reason: str) -> Verdict:
    return Verdict("need_answer", (reason,), missing)


def no(*reasons: str) -> Verdict:
    return Verdict("not_eligible", reasons)


def skip(*reasons: str) -> Verdict:
    return Verdict("insufficient", reasons)


@dataclass
class Scheme:
    id: str
    name: str
    authority: str
    portal: str
    documents: tuple[str, ...]
    spoken: dict[str, str]

    def judge(self, profile: Profile) -> Verdict:
        raise NotImplementedError


def _poor(profile: Profile, ceiling: int) -> str | None:
    """'yes' if a poverty signal is known, 'no' if clearly above, else None."""
    if profile.bpl is True or profile.ration in ("aay", "phh"):
        return "yes"
    if profile.annual_income is not None and profile.annual_income <= ceiling:
        return "yes"
    if profile.bpl is False and profile.annual_income is not None and profile.annual_income > ceiling:
        return "no"
    if profile.ration == "none" and profile.annual_income is not None and profile.annual_income > ceiling:
        return "no"
    return None


@dataclass
class PMKisan(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.occupation and profile.occupation != "farmer":
            return no("Occupation is not farming.")
        if profile.occupation != "farmer":
            return need("occupation", reason="Occupation is not known yet.")
        if profile.land_acres is None:
            return need("land_acres", reason="Land size is not known yet.")
        if profile.land_acres <= 0:
            return no("No landholding was mentioned.")
        if profile.annual_income is not None and profile.annual_income > 250000:
            return no("Income looks above the usual PM-KISAN exclusion. The CSC will confirm.")
        return qualify(f"Landholding farmer, {profile.land_acres:g} acres.")


@dataclass
class PMFBY(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.occupation and profile.occupation != "farmer":
            return no("Crop insurance is for farmers.")
        if profile.occupation != "farmer":
            return need("occupation", reason="Occupation is not known yet.")
        if not profile.crop:
            return need("crop", reason="Crop is not known yet.")
        if profile.crop_loss:
            return qualify(f"Farmer growing {profile.crop}, and this season's crop was damaged.")
        return qualify(f"Farmer growing {profile.crop}.")


@dataclass
class PMJAY(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        poor = _poor(profile, 120000)
        if poor == "yes":
            return qualify("BPL, priority ration, or a low family income - the usual Ayushman path.")
        if poor == "no":
            return no("Household does not look like the Ayushman deprivation list. The CSC can still check SECC.")
        return need("bpl", reason="Need the ration card or BPL status for Ayushman Bharat.")


@dataclass
class VayVandana(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        ages = [age for age in (profile.age, profile.senior_age) if age is not None]
        if not ages:
            return need("age", reason="Age in the house is not known yet.")
        if max(ages) >= 70:
            who = "the caller" if (profile.age or 0) >= 70 else "a family member"
            return qualify(f"{who.capitalize()} is 70 or older. Vay Vandana covers every citizen in that age.")
        return no("Nobody mentioned in the house is 70 yet.")


@dataclass
class Vishwakarma(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.occupation == "artisan" or profile.artisan_trade:
            trade = profile.artisan_trade or "a traditional trade"
            return qualify(f"Works in {trade}. PM Vishwakarma covers that kind of craft.")
        if profile.occupation:
            return no("Occupation is not a traditional craft covered by PM Vishwakarma.")
        return need("occupation", reason="Occupation is not known yet.")


@dataclass
class PMAYGramin(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.area == "urban":
            return no("PMAY-Gramin is for village houses. Ask the CSC about PMAY-Urban separately.")
        if profile.area != "rural":
            return need("area", reason="Village or town is not known yet.")
        if profile.housing == "pucca":
            return no("The house was described as pucca.")
        if profile.housing not in ("kutcha", "homeless"):
            return need("housing", reason="The house type is not known yet.")
        poor = _poor(profile, 150000)
        if poor == "yes":
            return qualify("Kutcha or no house, in a village, with a poverty signal.")
        if poor == "no":
            return no("The house is kutcha, but income looks above the usual PMAY-G band.")
        return likely("Kutcha house in a village. The CSC will check the deprivation list.")


@dataclass
class Ujjwala(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.gender == "man":
            return no("Ujjwala connections are issued to an adult woman in the house.")
        if profile.gender != "woman":
            return need("gender", reason="Need to know if an adult woman will hold the connection.")
        if profile.lpg is True:
            return no("The house already has an LPG cylinder.")
        if profile.lpg is not False:
            return need("lpg", reason="LPG connection is not known yet.")
        poor = _poor(profile, 180000)
        if poor == "yes":
            return qualify("Woman in a household without LPG, with a poverty signal.")
        if poor == "no":
            return no("No LPG, but the income band looks above Ujjwala.")
        return need("bpl", reason="Need BPL or ration status for Ujjwala.")


@dataclass
class MGNREGA(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.area == "urban":
            return no("MGNREGA job cards are for rural households.")
        if profile.area != "rural":
            return need("area", reason="Village or town is not known yet.")
        if profile.age is not None and profile.age < 18:
            return no("The caller is under 18. An adult in the house can still ask for a job card.")
        return qualify("Rural adult household. Ask the CSC for a job card, or for work if one already exists.")


@dataclass
class IGNOAPS(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        ages = [age for age in (profile.age, profile.senior_age) if age is not None]
        if not ages:
            return need("age", reason="Age is not known yet.")
        if max(ages) < 60:
            return no("Nobody mentioned is 60 yet.")
        poor = _poor(profile, 100000)
        who = "The caller" if (profile.age or 0) >= 60 else "A family member"
        if poor == "yes":
            return qualify(f"{who} is 60 or older and the household has a poverty signal.")
        if poor == "no":
            return no("Someone is 60 or older, but income looks above the NSAP band.")
        return need("bpl", reason="Need BPL or ration status for the old-age pension.")


@dataclass
class IGNWPS(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.widow is False:
            return no("Widow status was answered no.")
        if profile.widow is not True:
            if profile.gender == "woman" and profile.age is not None and profile.age >= 40:
                return need("widow", reason="Widow status is not known yet.")
            return skip("Widow pension is only asked when it might apply.")
        if profile.age is not None and profile.age < 40:
            return no("NSAP widow pension usually starts at 40.")
        if profile.age is None:
            return need("age", reason="Age is not known yet.")
        poor = _poor(profile, 100000)
        if poor == "yes":
            return qualify("Widow, 40 or older, with a poverty signal.")
        if poor == "no":
            return no("Widow, but income looks above the NSAP band.")
        return need("bpl", reason="Need BPL or ration status for the widow pension.")


@dataclass
class DisabilityPension(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.disability is False:
            return no("Disability was answered no.")
        if profile.disability is not True:
            return skip("Disability pension is only asked when disability is mentioned.")
        if profile.age is not None and profile.age < 18:
            return no("NSAP disability pension is for adults. Ask the CSC about child disability support.")
        poor = _poor(profile, 100000)
        if poor == "yes":
            return qualify("Disability noted, with a poverty signal.")
        if poor == "no":
            return no("Disability noted, but income looks above the NSAP band.")
        return likely("Disability noted. Carry the disability certificate. The CSC will check the income band.")


@dataclass
class PMMVY(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.gender == "man":
            return no("Matru Vandana is paid to the mother.")
        if profile.pregnant is False:
            return no("No pregnancy or recent birth was mentioned.")
        if profile.pregnant is True:
            return qualify("Pregnancy or a new mother was mentioned. The CSC confirms it is the first living child.")
        return skip("Matru Vandana is asked when pregnancy is mentioned.")


@dataclass
class SVANidhi(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.occupation == "street_vendor":
            return qualify("Street vendor. PM SVANidhi is a small working-capital loan for a vendor stall.")
        if profile.occupation:
            return no("Not described as a street vendor.")
        return skip("Vendor loan is checked once occupation is known.")


@dataclass
class EShram(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        unorganised = {"farmer", "artisan", "street_vendor", "labourer", "homemaker", "other"}
        if profile.occupation in ("salaried", "student"):
            return no("e-Shram is the register for unorganised workers.")
        if profile.occupation in unorganised:
            return qualify("Unorganised work. e-Shram registration is free at the CSC.")
        return need("occupation", reason="Occupation is not known yet.")


@dataclass
class JanDhan(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.bank_account is False:
            return qualify("No bank account yet. PM Jan Dhan can be opened at the CSC.")
        if profile.bank_account is True:
            return no("A bank account already exists.")
        return need("bank_account", reason="Bank account is not known yet.")


@dataclass
class GruhaLakshmi(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.state and profile.state != "KA":
            return no("Gruha Lakshmi is a Karnataka scheme.")
        if profile.state != "KA":
            return skip("State is not known yet, so the Karnataka scheme stays aside.")
        if profile.gender == "man":
            return no("Gruha Lakshmi is paid to the woman head of the family.")
        if profile.gender != "woman":
            return need("gender", reason="Need to know if a woman heads the family.")
        poor = _poor(profile, 180000)
        if poor == "yes":
            return qualify("Woman in a Karnataka household with a poverty signal.")
        if poor == "no":
            return no("Karnataka woman, but income looks above the Gruha Lakshmi band.")
        return need("bpl", reason="Need BPL or ration status for Gruha Lakshmi.")


@dataclass
class LadkiBahin(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.state and profile.state != "MH":
            return no("Ladki Bahin is a Maharashtra scheme.")
        if profile.state != "MH":
            return skip("State is not known yet, so the Maharashtra scheme stays aside.")
        if profile.gender == "man":
            return no("Ladki Bahin is for women.")
        if profile.gender != "woman":
            return need("gender", reason="Need to know if the applicant is a woman.")
        if profile.age is None:
            return need("age", reason="Age is not known yet.")
        if profile.age < 21 or profile.age > 65:
            return no("Ladki Bahin is for women aged 21 to 65.")
        if profile.annual_income is not None and profile.annual_income > 250000 and profile.bpl is not True:
            return no("Family income looks above the Ladki Bahin cap of Rs 2.5 lakh.")
        if profile.bpl is True or (profile.annual_income is not None and profile.annual_income <= 250000):
            return qualify("Maharashtra woman, age 21 to 65, within the income signal.")
        return likely("Maharashtra woman, age 21 to 65. The CSC will check the family income cap.")


@dataclass
class RythuBharosa(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.state and profile.state != "TG":
            return no("Rythu Bharosa is a Telangana farmer scheme.")
        if profile.state != "TG":
            return skip("State is not known yet, so the Telangana scheme stays aside.")
        if profile.occupation and profile.occupation != "farmer":
            return no("Rythu Bharosa is for farmers.")
        if profile.occupation != "farmer":
            return need("occupation", reason="Occupation is not known yet.")
        if profile.land_acres is None:
            return need("land_acres", reason="Land size is not known yet.")
        if profile.land_acres <= 0:
            return no("No landholding was mentioned.")
        return qualify(f"Telangana farmer with {profile.land_acres:g} acres.")


@dataclass
class LakshmirBhandar(Scheme):
    def judge(self, profile: Profile) -> Verdict:
        if profile.state and profile.state != "WB":
            return no("Lakshmir Bhandar is a West Bengal scheme.")
        if profile.state != "WB":
            return skip("State is not known yet, so the West Bengal scheme stays aside.")
        if profile.gender == "man":
            return no("Lakshmir Bhandar is paid to women.")
        if profile.gender != "woman":
            return need("gender", reason="Need to know if the applicant is a woman.")
        if profile.age is None:
            return need("age", reason="Age is not known yet.")
        if profile.age < 25 or profile.age > 60:
            return no("Lakshmir Bhandar is generally for women aged 25 to 60.")
        return qualify("Woman in West Bengal, age 25 to 60. The amount differs for general and SC/ST households.")


CATALOG: tuple[Scheme, ...] = (
    PMKisan(
        id="pm_kisan",
        name="PM-KISAN",
        authority="Government of India",
        portal="pmkisan.gov.in",
        documents=("Aadhaar", "Land record (7/12, pahani, or pattadar passbook)", "Bank passbook"),
        spoken=_names("पीएम किसान", "PM-Kisan", "ಪಿಎಂ ಕಿಸಾನ್", "పీఎం కిసాన్", "பிஎம் கிசான்", "पीएम किसान", "পিএম কিসান", "പിഎം കിസാൻ"),
    ),
    PMFBY(
        id="pmfby",
        name="PM Fasal Bima",
        authority="Government of India",
        portal="pmfby.gov.in",
        documents=("Aadhaar", "Land record", "Bank passbook", "Sowing details"),
        spoken=_names("फसल बीमा", "PM Fasal Bima", "ಬೆಳೆ ವಿಮೆ", "పంట బీమా", "பயிர் காப்பீடு", "पीक विमा", "ফসল বিমা", "വിള ഇൻഷുറൻസ്"),
    ),
    PMJAY(
        id="pmjay",
        name="Ayushman Bharat",
        authority="Government of India",
        portal="beneficiary.nha.gov.in",
        documents=("Aadhaar", "Ration card or SECC record"),
        spoken=_names("आयुष्मान भारत", "Ayushman Bharat", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್", "ఆయుష్మాన్ భారత్", "ஆயுஷ்மான் பாரத்", "आयुष्मान भारत", "আয়ুষ্মান ভারত", "ആയുഷ്മാൻ ഭാരത്"),
    ),
    VayVandana(
        id="vay_vandana",
        name="Ayushman Vay Vandana",
        authority="Government of India",
        portal="beneficiary.nha.gov.in",
        documents=("Aadhaar", "Age proof of the person who is 70 or older"),
        spoken=_names("वय वंदना", "Vay Vandana", "ವಯ್ ವಂದನ", "వయ్ వందన", "வய வந்தனா", "वय वंदना", "আয়ুষ্মান বয় বন্দনা", "വയ് വന്ദന"),
    ),
    Vishwakarma(
        id="vishwakarma",
        name="PM Vishwakarma",
        authority="Government of India",
        portal="pmvishwakarma.gov.in",
        documents=("Aadhaar", "Trade self-declaration or certificate", "Bank passbook"),
        spoken=_names("पीएम विश्वकर्मा", "PM Vishwakarma", "ಪಿಎಂ ವಿಶ್ವಕರ್ಮ", "పీఎం విశ్వకర్మ", "பிஎம் விஸ்வகர்மா", "पीएम विश्वकर्मा", "পিএম বিশ্বকর্মা", "പിഎം വിശ്വകർമ്മ"),
    ),
    PMAYGramin(
        id="pmay_g",
        name="PMAY-Gramin",
        authority="Government of India",
        portal="pmayg.nic.in",
        documents=("Aadhaar", "Ration or BPL proof", "Gram sabha note or house photo"),
        spoken=_names("पीएम आवास", "PMAY-Gramin", "ಪಿಎಂ ಆವಾಸ್", "పీఎం ఆవాస్", "பிஎம் ஆவாஸ்", "पीएम आवास", "পিএম আবাস", "പിഎം ആവാസ്"),
    ),
    Ujjwala(
        id="ujjwala",
        name="PM Ujjwala",
        authority="Government of India",
        portal="pmuy.gov.in",
        documents=("Aadhaar of the woman", "BPL or ration card", "Bank passbook"),
        spoken=_names("उज्ज्वला", "Ujjwala", "ಉಜ್ಜ್ವಲ", "ఉజ్వల", "உஜ்ஜ்வலா", "उज्ज्वला", "উজ্জ্বলা", "ഉജ്ജ്വല"),
    ),
    MGNREGA(
        id="mgnrega",
        name="MGNREGA",
        authority="Government of India",
        portal="nrega.nic.in",
        documents=("Aadhaar", "Bank passbook", "Address proof from the village"),
        spoken=_names("मनरेगा", "MGNREGA", "ಮನರೇಗಾ", "మనరేగా", "மன்ரேகா", "मनरेगा", "মনরেগা", "മൻരേഗ"),
    ),
    IGNOAPS(
        id="ignoaps",
        name="Old-age pension (NSAP)",
        authority="Government of India",
        portal="nsap.nic.in",
        documents=("Aadhaar", "Age proof", "BPL or ration card", "Bank passbook"),
        spoken=_names("बुढ़ापा पेंशन", "Old-age pension", "ಮುಪ್ಪಿನ ಪಿಂಚಣಿ", "వృద్ధాప్య పింఛను", "முதியோர் ஓய்வூதியம்", "वृद्धापकाळ पेन्शन", "বার্ধক্য পেনশন", "വാർദ്ധക്യ പെൻഷൻ"),
    ),
    IGNWPS(
        id="ignwps",
        name="Widow pension (NSAP)",
        authority="Government of India",
        portal="nsap.nic.in",
        documents=("Aadhaar", "Husband's death certificate", "Age proof", "BPL or ration card", "Bank passbook"),
        spoken=_names("विधवा पेंशन", "Widow pension", "ವಿಧವಾ ಪಿಂಚಣಿ", "వితంతు పింఛను", "விதவை ஓய்வூதியம்", "विधवा पेन्शन", "বিধবা পেনশন", "വിധവാ പെൻഷൻ"),
    ),
    DisabilityPension(
        id="igndps",
        name="Disability pension (NSAP)",
        authority="Government of India",
        portal="nsap.nic.in",
        documents=("Aadhaar", "Disability certificate", "BPL or ration card", "Bank passbook"),
        spoken=_names("दिव्यांग पेंशन", "Disability pension", "ದಿವ್ಯಾಂಗ ಪಿಂಚಣಿ", "వికలాంగ పింఛను", "மாற்றுத்திறன் ஓய்வூதியம்", "दिव्यांग पेन्शन", "প্রতিবন্ধী পেনশন", "ഭിന്നശേഷി പെൻഷൻ"),
    ),
    PMMVY(
        id="pmmvy",
        name="PM Matru Vandana",
        authority="Government of India",
        portal="pmmvy.wcd.gov.in",
        documents=("Aadhaar", "MCP card or ANM note", "Bank passbook"),
        spoken=_names("मातृ वंदना", "Matru Vandana", "ಮಾತೃ ವಂದನ", "మాతృ వందన", "மாத்ரு வந்தனா", "मातृ वंदना", "মাতৃ বন্দনা", "മാതൃ വന്ദന"),
    ),
    SVANidhi(
        id="svanidhi",
        name="PM SVANidhi",
        authority="Government of India",
        portal="pmsvanidhi.mohua.gov.in",
        documents=("Aadhaar", "Vendor letter from the local body, or a survey slip", "Bank passbook"),
        spoken=_names("पीएम स्वनिधि", "PM SVANidhi", "ಪಿಎಂ ಸ್ವನಿಧಿ", "పీఎం స్వనిధి", "பிஎம் ஸ்வநிதி", "पीएम स्वनिधी", "পিএম স্বনিধি", "പിഎം സ്വനിധി"),
    ),
    EShram(
        id="eshram",
        name="e-Shram",
        authority="Government of India",
        portal="eshram.gov.in",
        documents=("Aadhaar", "Bank passbook"),
        spoken=_names("ई-श्रम", "e-Shram", "ಈ ಶ್ರಮ್", "ఈ శ్రమ్", "ஈ ஸ்ரம்", "ई-श्रम", "ই শ্রম", "ഈ ശ്രം"),
    ),
    JanDhan(
        id="jandhan",
        name="PM Jan Dhan",
        authority="Government of India",
        portal="pmjdy.gov.in",
        documents=("Aadhaar",),
        spoken=_names("जन धन", "Jan Dhan", "ಜನ್ ಧನ್", "జన్ ధన్", "ஜன் தன்", "जन धन", "জন ধন", "ജൻ ധൻ"),
    ),
    GruhaLakshmi(
        id="gruha_lakshmi",
        name="Gruha Lakshmi",
        authority="Karnataka",
        portal="sevasindhu.karnataka.gov.in",
        documents=("Aadhaar of the woman", "BPL or ration card", "Bank passbook of the woman"),
        spoken=_names("गृह लक्ष्मी", "Gruha Lakshmi", "ಗೃಹ ಲಕ್ಷ್ಮಿ", "గృహ లక్ష్మి", "கிருஹ லட்சுமி", "गृह लक्ष्मी", "গৃহ লক্ষ্মী", "ഗൃഹ ലക്ഷ്മി"),
    ),
    LadkiBahin(
        id="ladki_bahin",
        name="Ladki Bahin",
        authority="Maharashtra",
        portal="ladakibahin.maharashtra.gov.in",
        documents=("Aadhaar", "Domicile or ration card", "Bank passbook", "Income declaration"),
        spoken=_names("लाडकी बहीण", "Ladki Bahin", "ಲಾಡಕಿ ಬಹಿಣ್", "లాడ్కీ బహిన్", "லாட்கி பஹின்", "लाडकी बहिण", "লাডকি বহিন", "ലാഡ്കി ബഹിൻ"),
    ),
    RythuBharosa(
        id="rythu_bharosa",
        name="Rythu Bharosa",
        authority="Telangana",
        portal="rythubharosa.telangana.gov.in",
        documents=("Aadhaar", "Pattadar passbook", "Bank passbook"),
        spoken=_names("रायथु भरोसा", "Rythu Bharosa", "ರೈತು ಭರೋಸಾ", "రైతు భరోసా", "ரைது பரோசா", "रायतू भरोसा", "রাইথু ভরোসা", "രൈതു ഭരോസ"),
    ),
    LakshmirBhandar(
        id="lakshmir_bhandar",
        name="Lakshmir Bhandar",
        authority="West Bengal",
        portal="wb.gov.in",
        documents=("Aadhaar", "Age proof", "Bank passbook"),
        spoken=_names("लक्ष्मीर भंडार", "Lakshmir Bhandar", "ಲಕ್ಷ್ಮೀರ್ ಭಂಡಾರ್", "లక్ష్మీర్ భండార్", "லக்ஷ்மீர் பண்டார்", "लक्ष्मीर भांडार", "লক্ষ্মীর ভান্ডার", "ലക്ഷ്മീർ ഭണ്ഡാർ"),
    ),
)

CATALOG_BY_ID = {scheme.id: scheme for scheme in CATALOG}

STATUS_ORDER = {
    "qualify": 0,
    "likely": 1,
    "need_answer": 2,
    "not_eligible": 3,
    "insufficient": 4,
}


@dataclass
class Match:
    scheme_id: str
    name: str
    authority: str
    portal: str
    status: str
    reasons: list[str]
    missing: list[str]
    documents: list[str]
    spoken: dict[str, str]

    def as_dict(self) -> dict:
        return {
            "id": self.scheme_id,
            "name": self.name,
            "authority": self.authority,
            "portal": self.portal,
            "status": self.status,
            "reasons": self.reasons,
            "missing": self.missing,
            "documents": self.documents,
            "spoken": self.spoken,
        }


def match_all(profile: Profile) -> list[Match]:
    found: list[Match] = []
    for scheme in CATALOG:
        verdict = scheme.judge(profile)
        found.append(
            Match(
                scheme_id=scheme.id,
                name=scheme.name,
                authority=scheme.authority,
                portal=scheme.portal,
                status=verdict.status,
                reasons=list(verdict.reasons),
                missing=list(verdict.missing),
                documents=list(scheme.documents),
                spoken=scheme.spoken,
            )
        )
    catalog_order = {scheme.id: index for index, scheme in enumerate(CATALOG)}
    found.sort(key=lambda item: (STATUS_ORDER.get(item.status, 9), catalog_order[item.scheme_id]))
    return found


def spoken_name(match: Match, language: str) -> str:
    return match.spoken.get(language) or match.spoken.get("en") or match.name


AUDIT_FIELDS = ("name_match", "mobile_linked", "bank_account")

NEXT_PRIORITY = (
    "district",
    "occupation",
    "land_acres",
    "age",
    "area",
    "gender",
    "bpl",
    "crop",
    "senior_age",
    "housing",
    "lpg",
    "widow",
    "pregnant",
    "bank_account",
    "name_match",
    "mobile_linked",
    "annual_income",
)


def next_field(profile: Profile, matches: list[Match]) -> str | None:
    """Ask the CSC rejection checks once two schemes are in reach. Otherwise ask the fact that unlocks the most."""
    good = [item for item in matches if item.status in ("qualify", "likely")]
    if len(good) >= 2:
        for field in AUDIT_FIELDS:
            if getattr(profile, field) is None:
                return field
        return None

    scores: dict[str, int] = {}
    for item in matches:
        if item.status != "need_answer":
            continue
        for field in item.missing:
            scores[field] = scores.get(field, 0) + 1
    if profile.district is None and profile.state is None:
        scores["district"] = scores.get("district", 0) + 6
    if profile.occupation is None:
        scores["occupation"] = scores.get("occupation", 0) + 1
    if profile.occupation == "farmer" and profile.land_acres is None:
        scores["land_acres"] = scores.get("land_acres", 0) + 3
    if profile.age is None:
        scores["age"] = scores.get("age", 0) + 1
    if not scores:
        return None

    def rank(item: tuple[str, int]) -> tuple[int, int]:
        field, score = item
        priority = NEXT_PRIORITY.index(field) if field in NEXT_PRIORITY else 50
        return (-score, priority)

    return sorted(scores.items(), key=rank)[0][0]


def documents_for(matches: list[Match]) -> list[str]:
    seen: list[str] = []
    for item in matches:
        if item.status not in ("qualify", "likely"):
            continue
        for doc in item.documents:
            if doc not in seen:
                seen.append(doc)
    return seen


def fix_first(profile: Profile) -> list[str]:
    notes: list[str] = []
    if profile.name_match is False:
        notes.append(
            "Aadhaar and ration card names do not match. Correct the name before the CSC submits the form, or the application can be rejected."
        )
    if profile.mobile_linked is False:
        notes.append("Mobile is not linked to Aadhaar. Link it at the CSC or an Aadhaar centre first.")
    if profile.bank_account is False:
        notes.append("No bank account yet. Open PM Jan Dhan at the CSC before any scheme that pays into a bank.")
    if profile.bank_account is True and profile.aadhaar_seeded is False:
        notes.append("Bank account is not seeded with Aadhaar. Seed it, or the payment can fail.")
    return notes


def slip_level(profile: Profile, matches: list[Match]) -> str:
    good = any(item.status in ("qualify", "likely") for item in matches)
    audits_done = all(getattr(profile, field) is not None for field in AUDIT_FIELDS)
    if good and audits_done:
        return "ready"
    if good:
        return "draft"
    return "early"


def csc_text(profile: Profile) -> str:
    place_bits = [bit for bit in (profile.district, profile.state_name) if bit]
    place = ", ".join(place_bits) if place_bits else "your block"
    return (
        f"Nearest CSC: take this slip to the Common Service Centre for {place}. "
        "The gram panchayat or the taluk office can point you to the counter. "
        "Someone with a phone can open the CSC locator at csc.gov.in and search the district. "
        "Hand over the slip and say the scheme names. Pay only the fee printed on the official CSC receipt. "
        "Do not share an OTP, Aadhaar number, or PAN with anyone who calls you back."
    )
