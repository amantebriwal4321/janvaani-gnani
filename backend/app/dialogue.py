"""Short spoken lines. Eligibility stays in the rule engine; this file only phrases the next step."""

from __future__ import annotations

from app.models import Profile

LANGS = ("hi", "hi-en", "en", "kn", "te", "ta", "mr", "bn", "ml")


class _Safe(dict):
    def __missing__(self, key: str) -> str:
        return ""


def say(key: str, language: str, **kwargs) -> str:
    table = STRINGS[key]
    template = table.get(language) or table.get("hi") or table["en"]
    return template.format_map(_Safe(**kwargs))


STRINGS: dict[str, dict[str, str]] = {
    "greeting": {
        "hi": "नमस्ते। मैं जनवाणी हूँ। आप अपनी भाषा में बोलिए। मैं योजना का फ़ॉर्म भरूँगी, और सीएससी के लिए एक पर्ची बनाऊँगी।",
        "hi-en": "Namaste. Main JanVaani hoon. Aap apni language mein boliye. Main scheme ka form bharungi, aur CSC ke liye ek slip banaungi.",
        "en": "Namaste. I am JanVaani. Speak in your own language. I will fill the scheme form and make a CSC slip.",
        "kn": "ನಮಸ್ಕಾರ. ನಾನು ಜನವಾಣಿ. ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಮಾತನಾಡಿ. ನಾನು ಯೋಜನೆಯ ಫಾರ್ಮ್ ತುಂಬಿಸಿ, ಸಿಎಸ್‌ಸಿ ಚೀಟಿ ಮಾಡುತ್ತೇನೆ.",
        "te": "నమస్కారం. నేను జనవాణి. మీ భాషలో మాట్లాడండి. నేను పథకం ఫారం నింపి, సీఎస్‌సీ స్లిప్ ఇస్తాను.",
        "ta": "வணக்கம். நான் ஜன்வாணி. உங்கள் மொழியில் பேசுங்கள். திட்ட விண்ணப்பத்தை நிரப்பி, சிஎஸ்சி சீட்டு தருகிறேன்.",
        "mr": "नमस्कार. मी जनवाणी. तुमच्या भाषेत बोला. मी योजना अर्ज भरेन आणि सीएससी ची पर्ची देईन.",
        "bn": "নমস্কার। আমি জনবাণী। আপনার ভাষায় বলুন। আমি প্রকল্পের ফর্ম ভরে সিএসসি স্লিপ বানিয়ে দেব।",
        "ml": "നമസ്കാരം. ഞാൻ ജനവാണി. നിങ്ങളുടെ ഭാഷയിൽ പറയൂ. ഞാൻ പദ്ധതി ഫോറം നിറച്ച് സിഎസ്‌സി സ്ലിപ്പ് തരാം.",
    },
    "heard": {
        "hi": "मैंने यह सुना: {facts}.",
        "hi-en": "Maine yeh suna: {facts}.",
        "en": "I heard this: {facts}.",
        "kn": "ನಾನು ಹೀಗೆ ಕೇಳಿದೆ: {facts}.",
        "te": "నేను ఇలా విన్నాను: {facts}.",
        "ta": "நான் இப்படி கேட்டேன்: {facts}.",
        "mr": "मी हे ऐकले: {facts}.",
        "bn": "আমি এটা শুনেছি: {facts}.",
        "ml": "ഞാൻ ഇങ്ങനെ കേട്ടു: {facts}.",
    },
    "schemes_line": {
        "hi": "{schemes} आपके लिए दिख रही हैं।",
        "hi-en": "{schemes} aapke liye dikh rahe hain.",
        "en": "These look right for you: {schemes}.",
        "kn": "ನಿಮಗೆ ಇವು ಸರಿಹೊಂದುತ್ತವೆ: {schemes}.",
        "te": "మీకు ఇవి సరిపోతాయి: {schemes}.",
        "ta": "உங்களுக்கு இவை பொருந்தும்: {schemes}.",
        "mr": "तुमच्यासाठी ही दिसत आहेत: {schemes}.",
        "bn": "আপনার জন্য এগুলো মিলছে: {schemes}.",
        "ml": "നിങ്ങൾക്ക് ഇവ ചേരും: {schemes}.",
    },
    "and_more": {
        "hi": " और {n} और",
        "hi-en": " aur {n} aur",
        "en": " and {n} more",
        "kn": " ಮತ್ತು ಇನ್ನೂ {n}",
        "te": " ఇంకా {n}",
        "ta": " மேலும் {n}",
        "mr": " आणि आणखी {n}",
        "bn": " আরও {n}",
        "ml": " വീണ്ടും {n}",
    },
    "slip_ready": {
        "hi": "सीएससी पर्ची तैयार है। {schemes} के कागज़ ले जाइए।",
        "hi-en": "CSC slip ready hai. {schemes} ke papers le jaiye.",
        "en": "The CSC slip is ready. Carry the papers for {schemes}.",
        "kn": "ಸಿಎಸ್‌ಸಿ ಚೀಟಿ ತಯಾರಾಗಿದೆ. {schemes} ದಾಖಲೆ ತೆಗೆದುಕೊಂಡು ಹೋಗಿ.",
        "te": "సీఎస్‌సీ స్లిప్ సిద్ధం. {schemes} కాగితాలు తీసుకెళ్లండి.",
        "ta": "சிஎஸ்சி சீட்டு தயார். {schemes} ஆவணங்களை எடுத்துச் செல்லுங்கள்.",
        "mr": "सीएससी पर्ची तयार आहे. {schemes} ची कागदपत्रे न्या.",
        "bn": "সিএসসি স্লিপ তৈরি। {schemes}-এর কাগজ নিয়ে যান।",
        "ml": "സിഎസ്‌സി സ്ലിപ്പ് തയ്യാർ. {schemes} പേപ്പറുകൾ കൊണ്ടുപോകൂ.",
    },
    "ack": {
        "hi": "ठीक है, लिख लिया।",
        "hi-en": "Theek hai, likh liya.",
        "en": "All right, I have written that down.",
        "kn": "ಸರಿ, ಬರೆದುಕೊಂಡೆ.",
        "te": "సరే, రాశాను.",
        "ta": "சரி, எழுதிக்கொண்டேன்.",
        "mr": "ठीक आहे, लिहून घेतले.",
        "bn": "ঠিক আছে, লিখে নিলাম।",
        "ml": "ശരി, എഴുതി.",
    },
    "unclear": {
        "hi": "मैं फिर से सुनना चाहती हूँ। एक छोटी बात बताइए।",
        "hi-en": "Main phir se sunna chahti hoon. Ek chhoti baat bataiye.",
        "en": "I want to hear that once more. Tell me one small thing.",
        "kn": "ಇನ್ನೊಮ್ಮೆ ಹೇಳಿ. ಒಂದು ಚಿಕ್ಕ ಮಾತು ಸಾಕು.",
        "te": "మళ్ళీ చెప్పండి. ఒక చిన్న మాట చాలు.",
        "ta": "மீண்டும் சொல்லுங்கள். ஒரு சிறிய செய்தி போதும்.",
        "mr": "पुन्हा सांगा. एक छोटी गोष्ट पुरे.",
        "bn": "আরেকবার বলুন। একটা ছোট কথাই যথেষ্ট।",
        "ml": "ഒന്നുകൂടി പറയൂ. ഒരു ചെറിയ കാര്യം മതി.",
    },
    "invite": {
        "hi": "और कुछ बताना हो तो बोलिए।",
        "hi-en": "Aur kuchh batana ho to boliye.",
        "en": "Say more if there is anything else.",
        "kn": "ಇನ್ನೇನಾದರೂ ಇದ್ದರೆ ಹೇಳಿ.",
        "te": "ఇంకేమైనా ఉంటే చెప్పండి.",
        "ta": "வேறு ஏதாவது இருந்தால் சொல்லுங்கள்.",
        "mr": "आणखी काही असेल तर सांगा.",
        "bn": "আর কিছু বলার থাকলে বলুন।",
        "ml": "വേറെ എന്തെങ്കിലും ഉണ്ടെങ്കിൽ പറയൂ.",
    },
    "id_ignored": {
        "hi": "मैं आधार, पैन या फ़ोन नंबर नहीं लिखूँगी। बाकी बात बताइए।",
        "hi-en": "Main Aadhaar, PAN ya phone number nahi likhungi. Baaki baat bataiye.",
        "en": "I will not write an Aadhaar, PAN, or phone number. Tell me the rest.",
        "kn": "ನಾನು ಆಧಾರ್, ಪ್ಯಾನ್ ಅಥವಾ ಫೋನ್ ಸಂಖ್ಯೆ ಬರೆಯುವುದಿಲ್ಲ. ಉಳಿದ ಮಾತು ಹೇಳಿ.",
        "te": "నేను ఆధార్, పాన్ లేదా ఫోన్ నంబర్ రాయను. మిగతా మాట చెప్పండి.",
        "ta": "ஆதார், பான் அல்லது தொலைபேசி எண்ணை எழுதமாட்டேன். மற்றதைச் சொல்லுங்கள்.",
        "mr": "मी आधार, पॅन किंवा फोन नंबर लिहिणार नाही. बाकी सांगा.",
        "bn": "আমি আধার, প্যান বা ফোন নম্বর লিখব না। বাকিটা বলুন।",
        "ml": "ഞാൻ ആധാർ, പാൻ, ഫോൺ നമ്പർ എഴുതില്ല. ബാക്കി പറയൂ.",
    },
    "switched": {
        "hi": "ठीक है। अब मैं हिन्दी में बोलूँगी।",
        "hi-en": "Theek hai. Ab main Hinglish mein bolungi.",
        "en": "All right. I will speak English now.",
        "kn": "ಸರಿ. ಈಗ ನಾನು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ.",
        "te": "సరే. ఇప్పుడు నేను తెలుగులో మాట్లాడతాను.",
        "ta": "சரி. இனி தமிழில் பேசுகிறேன்.",
        "mr": "ठीक आहे. आता मी मराठीत बोलेन.",
        "bn": "ঠিক আছে। এখন বাংলায় বলব।",
        "ml": "ശരി. ഇനി ഞാൻ മലയാളത്തിൽ പറയാം.",
    },
    "ask_place": {
        "hi": "आप किस ज़िले और राज्य से हैं?",
        "hi-en": "Aap kis district aur state se hain?",
        "en": "Which district and state are you from?",
        "kn": "ನೀವು ಯಾವ ಜಿಲ್ಲೆ, ಯಾವ ರಾಜ್ಯದವರು?",
        "te": "మీరు ఏ జిల్లా, ఏ రాష్ట్రం?",
        "ta": "நீங்கள் எந்த மாவட்டம், எந்த மாநிலம்?",
        "mr": "तुम्ही कोणत्या जिल्ह्यात, कोणत्या राज्यात राहता?",
        "bn": "আপনি কোন জেলা, কোন রাজ্যের?",
        "ml": "നിങ്ങൾ ഏത് ജില്ല, ഏത് സംസ്ഥാനം?",
    },
    "ask_occupation": {
        "hi": "आप क्या काम करते हैं? खेती, मज़दूरी, दुकान, या कुछ और?",
        "hi-en": "Aap kya kaam karte hain? Kheti, mazdoori, dukaan, ya kuchh aur?",
        "en": "What work do you do? Farming, wage work, a shop, or something else?",
        "kn": "ನೀವು ಏನು ಕೆಲಸ ಮಾಡುತ್ತೀರಿ? ರೈತ, ಕೂಲಿ, ದರ್ಜಿ, ಅಂಗಡಿ?",
        "te": "మీరు ఏం పని చేస్తారు? రైతు, కూలీ, దర్జీ, దుకాణం?",
        "ta": "நீங்கள் என்ன வேலை செய்கிறீர்கள்? விவசாயம், கூலி, தையல், கடை?",
        "mr": "तुम्ही काय काम करता? शेती, मजुरी, शिवण, दुकान?",
        "bn": "আপনি কী কাজ করেন? চাষ, মজুরি, দর্জি, দোকান?",
        "ml": "നിങ്ങൾ എന്ത് ജോലി ചെയ്യുന്നു? കൃഷി, കൂലി, തയ്യൽ, കട?",
    },
    "ask_land": {
        "hi": "कितनी ज़मीन है? एकड़ में बताइए।",
        "hi-en": "Kitni zameen hai? Acre mein bataiye.",
        "en": "How much land is there? Tell me in acres.",
        "kn": "ಎಷ್ಟು ಎಕರೆ ಜಮೀನು?",
        "te": "ఎన్ని ఎకరాల భూమి?",
        "ta": "எத்தனை ஏக்கர் நிலம்?",
        "mr": "किती एकर जमीन आहे?",
        "bn": "কত একর জমি?",
        "ml": "എത്ര ഏക്കർ സ്ഥലം?",
    },
    "ask_age": {
        "hi": "आपकी उम्र कितनी है?",
        "hi-en": "Aapki umar kitni hai?",
        "en": "How old are you?",
        "kn": "ನಿಮ್ಮ ವಯಸ್ಸು ಎಷ್ಟು?",
        "te": "మీ వయసు ఎంత?",
        "ta": "உங்கள் வயது என்ன?",
        "mr": "तुमचे वय किती?",
        "bn": "আপনার বয়স কত?",
        "ml": "നിങ്ങളുടെ പ്രായം എത്ര?",
    },
    "ask_gender": {
        "hi": "क्या योजना महिला के नाम पर होगी? आप महिला हैं या पुरुष?",
        "hi-en": "Scheme aksar mahila ke naam par hoti hai. Aap mahila hain ya purush?",
        "en": "Many schemes are in a woman's name. Are you a woman or a man?",
        "kn": "ಅನೇಕ ಯೋಜನೆ ಮಹಿಳೆಯ ಹೆಸರಿನಲ್ಲಿ. ನೀವು ಹೆಂಗಸಾ, ಗಂಡಸಾ?",
        "te": "చాలా పథకాలు మహిళ పేరున. మీరు మహిళా, పురుషుడా?",
        "ta": "பல திட்டங்கள் பெண் பெயரில். நீங்கள் பெண்ணா, ஆணா?",
        "mr": "अनेक योजना महिलांच्या नावावर असतात. तुम्ही महिला आहात की पुरुष?",
        "bn": "অনেক প্রকল্প মহিলার নামে। আপনি মহিলা না পুরুষ?",
        "ml": "പല പദ്ധതിയും സ്ത്രീയുടെ പേരിൽ. നിങ്ങൾ സ്ത്രീയാണോ, പുരുഷനാണോ?",
    },
    "ask_bpl": {
        "hi": "क्या आपके पास बीपीएल या राशन कार्ड है?",
        "hi-en": "Kya aapke paas BPL ya ration card hai?",
        "en": "Do you have a BPL or ration card?",
        "kn": "ನಿಮ್ಮ ಬಳಿ ಬಿಪಿಎಲ್ ಅಥವಾ ರೇಷನ್ ಕಾರ್ಡ್ ಇದೆಯೇ?",
        "te": "మీకు బీపీఎల్ లేదా రేషన్ కార్డు ఉందా?",
        "ta": "உங்களிடம் பிபிஎல் அல்லது ரேஷன் கார்டு உள்ளதா?",
        "mr": "तुमच्याकडे बीपीएल किंवा रेशन कार्ड आहे का?",
        "bn": "আপনার কি বিপিএল বা রেশন কার্ড আছে?",
        "ml": "നിങ്ങൾക്ക് ബിപിഎൽ അല്ലെങ്കിൽ റേഷൻ കാർഡ് ഉണ്ടോ?",
    },
    "ask_crop": {
        "hi": "इस बार कौन सी फसल बोई है?",
        "hi-en": "Is baar kaun si fasal boyi hai?",
        "en": "Which crop did you sow this season?",
        "kn": "ಈ ಬಾರಿ ಯಾವ ಬೆಳೆ ಬಿತ್ತಿದ್ದೀರಿ?",
        "te": "ఈసారి ఏ పంట వేశారు?",
        "ta": "இந்த முறை எந்த பயிர் விதைத்தீர்கள்?",
        "mr": "या वेळी कोणते पीक पेरले?",
        "bn": "এবার কোন ফসল বুনেছেন?",
        "ml": "ഇത്തവണ ഏത് വിള വിതച്ചു?",
    },
    "ask_senior": {
        "hi": "घर में कोई साठ या सत्तर से ऊपर है?",
        "hi-en": "Ghar mein koi saath ya sattar se upar hai?",
        "en": "Is anyone at home over sixty or seventy?",
        "kn": "ಮನೆಯಲ್ಲಿ ಅರವತ್ತು ಅಥವಾ ಎಪ್ಪತ್ತು ದಾಟಿದವರು ಇದ್ದಾರೆಯೇ?",
        "te": "ఇంట్లో అరవై లేదా డెబ్బై దాటిన వారు ఉన్నారా?",
        "ta": "வீட்டில் அறுபது அல்லது எழுபது கடந்தவர் உண்டா?",
        "mr": "घरात कोणी साठ किंवा सत्तरच्या वर आहे का?",
        "bn": "ঘরে কি কেউ ষাট বা সত্তরের ওপরে?",
        "ml": "വീട്ടിൽ അറുപതോ എഴുപതോ കഴിഞ്ഞ ആരെങ്കിലും ഉണ്ടോ?",
    },
    "ask_area": {
        "hi": "आप गाँव में रहते हैं या शहर में?",
        "hi-en": "Aap gaon mein rehte hain ya shehar mein?",
        "en": "Do you live in a village or a town?",
        "kn": "ನೀವು ಹಳ್ಳಿಯಲ್ಲಿದ್ದೀರಾ, ನಗರದಲ್ಲಿದ್ದೀರಾ?",
        "te": "మీరు గ్రామంలోనా, పట్టణంలోనా?",
        "ta": "நீங்கள் கிராமத்திலா, நகரத்திலா?",
        "mr": "तुम्ही गावात राहता की शहरात?",
        "bn": "আপনি গ্রামে থাকেন না শহরে?",
        "ml": "നിങ്ങൾ ഗ്രാമത്തിലാണോ, നഗരത്തിലാണോ?",
    },
    "ask_housing": {
        "hi": "मकान कच्चा है या पक्का?",
        "hi-en": "Makaan kachcha hai ya pakka?",
        "en": "Is the house kutcha or pucca?",
        "kn": "ಮನೆ ಕಚ್ಚಾ ಅಥವಾ ಪಕ್ಕಾ?",
        "te": "ఇల్లు కచ్చా లేదా పక్కా?",
        "ta": "வீடு கச்சாவா, பக்காவா?",
        "mr": "घर कच्चे आहे की पक्के?",
        "bn": "ঘর কাঁচা না পাকা?",
        "ml": "വീട് കച്ചയാണോ, പക്കയാണോ?",
    },
    "ask_lpg": {
        "hi": "घर में गैस सिलेंडर है?",
        "hi-en": "Ghar mein gas cylinder hai?",
        "en": "Is there a gas cylinder at home?",
        "kn": "ಮನೆಯಲ್ಲಿ ಗ್ಯಾಸ್ ಸಿಲಿಂಡರ್ ಇದೆಯೇ?",
        "te": "ఇంట్లో గ్యాస్ సిలిండర్ ఉందా?",
        "ta": "வீட்டில் கேஸ் சிலிண்டர் உள்ளதா?",
        "mr": "घरात गॅस सिलिंडर आहे का?",
        "bn": "ঘরে গ্যাস সিলিন্ডার আছে?",
        "ml": "വീട്ടിൽ ഗ്യാസ് സിലിണ്ടർ ഉണ്ടോ?",
    },
    "ask_widow": {
        "hi": "क्या विधवा पेंशन पूछनी है?",
        "hi-en": "Kya widow pension poochhni hai?",
        "en": "Should I check the widow pension?",
        "kn": "ವಿಧವಾ ಪಿಂಚಣಿ ನೋಡಲೇ?",
        "te": "వితంతు పింఛను చూడాలా?",
        "ta": "விதவை ஓய்வூதியம் பார்க்கவா?",
        "mr": "विधवा पेन्शन पाहायची का?",
        "bn": "বিধবা পেনশন দেখব?",
        "ml": "വിധവാ പെൻഷൻ നോക്കണോ?",
    },
    "ask_pregnant": {
        "hi": "क्या घर में कोई महिला गर्भवती है या अभी माँ बनी है?",
        "hi-en": "Kya ghar mein koi mahila pregnant hai ya abhi maa bani hai?",
        "en": "Is a woman at home pregnant, or has she just had a baby?",
        "kn": "ಮನೆಯಲ್ಲಿ ಯಾರಾದರೂ ಗರ್ಭಿಣಿಯಾಗಿದ್ದಾರೆಯೇ, ಅಥವಾ ಈಗ ತಾಯಿಯಾಗಿದ್ದಾರೆಯೇ?",
        "te": "ఇంట్లో ఎవరైనా గర్భవతిగా ఉన్నారా, లేదా ఇప్పుడే తల్లి అయ్యారా?",
        "ta": "வீட்டில் யாராவது கர்ப்பமாக இருக்கிறார்களா, அல்லது இப்போது தாயானார்களா?",
        "mr": "घरात कोणी गर्भवती आहे का, किंवा आताच आई झाली आहे का?",
        "bn": "ঘরে কেউ গর্ভবতী, না এইমাত্র মা হয়েছেন?",
        "ml": "വീട്ടിൽ ആരെങ്കിലും ഗർഭിണിയാണോ, അല്ലെങ്കിൽ ഇപ്പോൾ അമ്മയായോ?",
    },
    "ask_bank": {
        "hi": "क्या आपका बैंक खाता है?",
        "hi-en": "Kya aapka bank account hai?",
        "en": "Do you have a bank account?",
        "kn": "ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆ ಇದೆಯೇ?",
        "te": "మీకు బ్యాంక్ ఖాతా ఉందా?",
        "ta": "உங்களுக்கு வங்கிக் கணக்கு உள்ளதா?",
        "mr": "तुमचे बँक खाते आहे का?",
        "bn": "আপনার ব্যাংক অ্যাকাউন্ট আছে?",
        "ml": "നിങ്ങൾക്ക് ബാങ്ക് അക്കൗണ്ട് ഉണ്ടോ?",
    },
    "ask_name_match": {
        "hi": "आधार और राशन कार्ड पर नाम एक जैसा है?",
        "hi-en": "Aadhaar aur ration card par naam ek jaisa hai?",
        "en": "Is the name the same on Aadhaar and the ration card?",
        "kn": "ಆಧಾರ್ ಮತ್ತು ರೇಷನ್ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಹೆಸರು ಒಂದೇ ಇದೆಯೇ?",
        "te": "ఆధార్ మరియు రేషన్ కార్డులో పేరు ఒకటేనా?",
        "ta": "ஆதாரும் ரேஷன் கார்டும் ஒரே பெயரில் உள்ளதா?",
        "mr": "आधार आणि रेशन कार्डवर नाव सारखे आहे का?",
        "bn": "আধার আর রেশন কার্ডে নাম কি এক?",
        "ml": "ആധാറിലും റേഷൻ കാർഡിലും പേര് ഒന്നാണോ?",
    },
    "ask_mobile": {
        "hi": "आधार पर मोबाइल नंबर जुड़ा है?",
        "hi-en": "Aadhaar par mobile number juda hai?",
        "en": "Is a mobile number linked to Aadhaar?",
        "kn": "ಆಧಾರ್‌ಗೆ ಮೊಬೈಲ್ ಸೇರಿದೆಯೇ?",
        "te": "ఆధార్‌కు మొబైల్ లింక్ అయిందా?",
        "ta": "ஆதாரில் மொபைல் இணைந்துள்ளதா?",
        "mr": "आधारला मोबाइल जोडला आहे का?",
        "bn": "আধারে মোবাইল যুক্ত আছে?",
        "ml": "ആധാറിൽ മൊബൈൽ ബന്ധിപ്പിച്ചിട്ടുണ്ടോ?",
    },
    "ask_seeded": {
        "hi": "बैंक खाते में आधार जुड़ा है?",
        "hi-en": "Bank account mein Aadhaar juda hai?",
        "en": "Is Aadhaar seeded in the bank account?",
        "kn": "ಬ್ಯಾಂಕ್ ಖಾತೆಗೆ ಆಧಾರ್ ಸೇರಿದೆಯೇ?",
        "te": "బ్యాంక్ ఖాతాలో ఆధార్ సీడ్ అయిందా?",
        "ta": "வங்கிக் கணக்கில் ஆதார் இணைந்துள்ளதா?",
        "mr": "बँक खात्यात आधार जोडला आहे का?",
        "bn": "ব্যাংক অ্যাকাউন্টে আধার যুক্ত আছে?",
        "ml": "ബാങ്ക് അക്കൗണ്ടിൽ ആധാർ ബന്ധിപ്പിച്ചിട്ടുണ്ടോ?",
    },
    "ask_income": {
        "hi": "परिवार की सालाना कमाई कितनी है? लाख में बताइए।",
        "hi-en": "Family ki saalana kamai kitni hai? Lakh mein bataiye.",
        "en": "What is the family's yearly income? Tell me in lakhs.",
        "kn": "ಕುಟುಂಬದ ವಾರ್ಷಿಕ ಆದಾಯ ಎಷ್ಟು? ಲಕ್ಷದಲ್ಲಿ ಹೇಳಿ.",
        "te": "కుటుంబ వార్షిక ఆదాయం ఎంత? లక్షల్లో చెప్పండి.",
        "ta": "குடும்ப ஆண்டு வருமானம் எவ்வளவு? லட்சத்தில் சொல்லுங்கள்.",
        "mr": "कुटुंबाचे वार्षिक उत्पन्न किती? लाखात सांगा.",
        "bn": "পরিবারের বার্ষিক আয় কত? লাখে বলুন।",
        "ml": "കുടുംബത്തിന്റെ വാർഷിക വരുമാനം എത്ര? ലക്ഷത്തിൽ പറയൂ.",
    },
    "fix_name": {
        "hi": "पहले नाम ठीक कराइए। आधार और राशन कार्ड पर नाम अलग है।",
        "hi-en": "Pehle naam theek karaiye. Aadhaar aur ration card par naam alag hai.",
        "en": "Fix the name first. It is different on Aadhaar and the ration card.",
        "kn": "ಮೊದಲು ಹೆಸರು ಸರಿಪಡಿಸಿ. ಆಧಾರ್ ಮತ್ತು ರೇಷನ್ ಕಾರ್ಡ್‌ನಲ್ಲಿ ಹೆಸರು ಬೇರೆ.",
        "te": "ముందు పేరు సరిచేయించండి. ఆధార్ మరియు రేషన్ కార్డులో పేరు వేరు.",
        "ta": "முதலில் பெயரைச் சரிசெய்யுங்கள். ஆதார் மற்றும் ரேஷன் கார்டில் பெயர் வேறு.",
        "mr": "आधी नाव दुरुस्त करून घ्या. आधार आणि रेशन कार्डवर नाव वेगळे आहे.",
        "bn": "আগে নাম ঠিক করান। আধার আর রেশন কার্ডে নাম আলাদা।",
        "ml": "ആദ്യം പേര് ശരിയാക്കൂ. ആധാറിലും റേഷൻ കാർഡിലും പേര് വേറെ.",
    },
    "fix_mobile": {
        "hi": "आधार पर मोबाइल नहीं जुड़ा है। पहले उसे जोड़िए।",
        "hi-en": "Aadhaar par mobile nahi juda hai. Pehle use jodiye.",
        "en": "The mobile is not linked to Aadhaar. Link it first.",
        "kn": "ಆಧಾರ್‌ಗೆ ಮೊಬೈಲ್ ಸೇರಿಲ್ಲ. ಮೊದಲು ಸೇರಿಸಿ.",
        "te": "ఆధార్‌కు మొబైల్ లింక్ కాలేదు. ముందు లింక్ చేయండి.",
        "ta": "ஆதாரில் மொபைல் இணையவில்லை. முதலில் இணைக்கவும்.",
        "mr": "आधारला मोबाइल जोडलेला नाही. आधी जोडा.",
        "bn": "আধারে মোবাইল যুক্ত নেই। আগে যুক্ত করুন।",
        "ml": "ആധാറിൽ മൊബൈൽ ബന്ധിപ്പിച്ചിട്ടില്ല. ആദ്യം ബന്ധിപ്പിക്കൂ.",
    },
    "fix_bank": {
        "hi": "बैंक खाता नहीं है। सीएससी पर जन धन खुलवाइए।",
        "hi-en": "Bank account nahi hai. CSC par Jan Dhan khulwaiye.",
        "en": "There is no bank account. Open Jan Dhan at the CSC.",
        "kn": "ಬ್ಯಾಂಕ್ ಖಾತೆ ಇಲ್ಲ. ಸಿಎಸ್‌ಸಿಯಲ್ಲಿ ಜನ್ ಧನ್ ತೆರೆಯಿರಿ.",
        "te": "బ్యాంక్ ఖాతా లేదు. సీఎస్‌సీలో జన్ ధన్ తెరవండి.",
        "ta": "வங்கிக் கணக்கு இல்லை. சிஎஸ்சியில் ஜன் தன் திறக்கவும்.",
        "mr": "बँक खाते नाही. सीएससीवर जन धन उघडा.",
        "bn": "ব্যাংক অ্যাকাউন্ট নেই। সিএসসিতে জন ধন খুলুন।",
        "ml": "ബാങ്ക് അക്കൗണ്ട് ഇല്ല. സിഎസ്‌സിയിൽ ജൻ ധൻ തുറക്കൂ.",
    },
}

QUESTION_KEY = {
    "district": "ask_place",
    "state": "ask_place",
    "state_name": "ask_place",
    "occupation": "ask_occupation",
    "land_acres": "ask_land",
    "age": "ask_age",
    "senior_age": "ask_senior",
    "gender": "ask_gender",
    "bpl": "ask_bpl",
    "ration": "ask_bpl",
    "crop": "ask_crop",
    "area": "ask_area",
    "housing": "ask_housing",
    "lpg": "ask_lpg",
    "widow": "ask_widow",
    "pregnant": "ask_pregnant",
    "bank_account": "ask_bank",
    "name_match": "ask_name_match",
    "mobile_linked": "ask_mobile",
    "aadhaar_seeded": "ask_seeded",
    "annual_income": "ask_income",
}

OCC_WORD = {
    "hi": {"farmer": "किसान", "artisan": "कारीगर", "street_vendor": "फेरी वाला", "labourer": "मज़दूर", "homemaker": "घर का काम", "student": "विद्यार्थी", "salaried": "नौकरी", "other": "दूसरा काम"},
    "hi-en": {"farmer": "kisan", "artisan": "karigar", "street_vendor": "thela", "labourer": "mazdoor", "homemaker": "ghar ka kaam", "student": "student", "salaried": "naukri", "other": "doosra kaam"},
    "en": {"farmer": "farmer", "artisan": "artisan", "street_vendor": "street vendor", "labourer": "wage worker", "homemaker": "homemaker", "student": "student", "salaried": "salaried job", "other": "other work"},
    "kn": {"farmer": "ರೈತ", "artisan": "ಕುಶಲಕರ್ಮಿ", "street_vendor": "ಬೀದಿ ವ್ಯಾಪಾರಿ", "labourer": "ಕೂಲಿ", "homemaker": "ಮನೆಕೆಲಸ", "student": "ವಿದ್ಯಾರ್ಥಿ", "salaried": "ನೌಕರಿ", "other": "ಬೇರೆ ಕೆಲಸ"},
    "te": {"farmer": "రైతు", "artisan": "చేతివృత్తి", "street_vendor": "వీధి వ్యాపారి", "labourer": "కూలీ", "homemaker": "ఇంటి పని", "student": "విద్యార్థి", "salaried": "ఉద్యోగం", "other": "ఇతర పని"},
    "ta": {"farmer": "விவசாயி", "artisan": "கைவினைஞர்", "street_vendor": "தெரு வியாபாரி", "labourer": "கூலி", "homemaker": "வீட்டு வேலை", "student": "மாணவர்", "salaried": "சம்பள வேலை", "other": "வேறு வேலை"},
    "mr": {"farmer": "शेतकरी", "artisan": "कारागीर", "street_vendor": "फेरीवाला", "labourer": "मजूर", "homemaker": "घरकाम", "student": "विद्यार्थी", "salaried": "नोकरी", "other": "इतर काम"},
    "bn": {"farmer": "চাষি", "artisan": "কারিগর", "street_vendor": "ফেরিওয়ালা", "labourer": "মজুর", "homemaker": "ঘরের কাজ", "student": "ছাত্র", "salaried": "চাকরি", "other": "অন্য কাজ"},
    "ml": {"farmer": "കർഷകൻ", "artisan": "കൈത്തൊഴിലാളി", "street_vendor": "തെരുവ് വ്യാപാരി", "labourer": "കൂലി", "homemaker": "വീട്ടുജോലി", "student": "വിദ്യാർഥി", "salaried": "ശമ്പള ജോലി", "other": "മറ്റ് ജോലി"},
}

LAND_UNIT = {
    "hi": "एकड़",
    "hi-en": "acre",
    "en": "acres",
    "kn": "ಎಕರೆ",
    "te": "ఎకరాలు",
    "ta": "ஏக்கர்",
    "mr": "एकर",
    "bn": "একর",
    "ml": "ഏക്കർ",
}
AGE_UNIT = {
    "hi": "साल",
    "hi-en": "saal",
    "en": "years",
    "kn": "ವರ್ಷ",
    "te": "ఏళ్లు",
    "ta": "வயது",
    "mr": "वर्षे",
    "bn": "বছর",
    "ml": "വയസ്",
}


def _occ(value: str, language: str) -> str:
    return OCC_WORD.get(language, OCC_WORD["en"]).get(value, value)


def describe_updates(profile: Profile, fields: list[str], language: str) -> str:
    bits: list[str] = []
    used = set(fields)
    if "district" in used or "state_name" in used:
        if profile.district and profile.state_name:
            bits.append(f"{profile.district}, {profile.state_name}")
        elif profile.district:
            bits.append(profile.district)
        elif profile.state_name:
            bits.append(profile.state_name)
    if "area" in used and profile.area:
        bits.append({"rural": {"hi": "गाँव", "hi-en": "gaon", "en": "village", "kn": "ಹಳ್ಳಿ", "te": "గ్రామం", "ta": "கிராமம்", "mr": "गाव", "bn": "গ্রাম", "ml": "ഗ്രാമം"}, "urban": {"hi": "शहर", "hi-en": "shehar", "en": "town", "kn": "ನಗರ", "te": "పట్టణం", "ta": "நகரம்", "mr": "शहर", "bn": "শহর", "ml": "നഗരം"}}[profile.area].get(language, profile.area))
    if "occupation" in used and profile.occupation:
        bits.append(_occ(profile.occupation, language))
    if "artisan_trade" in used and profile.artisan_trade and "occupation" not in used:
        bits.append(profile.artisan_trade)
    if "land_acres" in used and profile.land_acres is not None:
        bits.append(f"{profile.land_acres:g} {LAND_UNIT.get(language, 'acres')}")
    if "crop" in used and profile.crop:
        bits.append(profile.crop)
    if "crop_loss" in used and profile.crop_loss:
        bits.append({"hi": "फसल खराब", "hi-en": "fasal kharab", "en": "crop damaged", "kn": "ಬೆಳೆ ಹಾನಿ", "te": "పంట నష్టం", "ta": "பயிர் சேதம்", "mr": "पीक खराब", "bn": "ফসল নষ্ট", "ml": "വിള നഷ്ടം"}.get(language, "crop damaged"))
    if "age" in used and profile.age is not None:
        bits.append(f"{profile.age} {AGE_UNIT.get(language, 'years')}")
    if "senior_age" in used and profile.senior_age is not None:
        elder = {"hi": "घर में", "hi-en": "ghar mein", "en": "at home", "kn": "ಮನೆಯಲ್ಲಿ", "te": "ఇంట్లో", "ta": "வீட்டில்", "mr": "घरात", "bn": "ঘরে", "ml": "വീട്ടിൽ"}.get(language, "at home")
        bits.append(f"{elder} {profile.senior_age} {AGE_UNIT.get(language, 'years')}")
    if "gender" in used and profile.gender:
        bits.append({"woman": {"hi": "महिला", "hi-en": "mahila", "en": "woman", "kn": "ಹೆಂಗಸು", "te": "మహిళ", "ta": "பெண்", "mr": "महिला", "bn": "মহিলা", "ml": "സ്ത്രീ"}, "man": {"hi": "पुरुष", "hi-en": "purush", "en": "man", "kn": "ಗಂಡಸು", "te": "పురుషుడు", "ta": "ஆண்", "mr": "पुरुष", "bn": "পুরুষ", "ml": "പുരുഷൻ"}}.get(profile.gender, {}).get(language, profile.gender))
    if "bpl" in used and profile.bpl is True:
        bits.append("BPL")
    if "name_match" in used and profile.name_match is False:
        bits.append({"hi": "नाम अलग है", "hi-en": "naam alag hai", "en": "names differ", "kn": "ಹೆಸರು ಬೇರೆ", "te": "పేరు వేరు", "ta": "பெயர் வேறு", "mr": "नाव वेगळे", "bn": "নাম আলাদা", "ml": "പേര് വേറെ"}.get(language, "names differ"))
    if "bank_account" in used and profile.bank_account is False:
        bits.append({"hi": "बैंक खाता नहीं", "hi-en": "bank account nahi", "en": "no bank account", "kn": "ಬ್ಯಾಂಕ್ ಖಾತೆ ಇಲ್ಲ", "te": "బ్యాంక్ ఖాతా లేదు", "ta": "வங்கிக் கணக்கு இல்லை", "mr": "बँक खाते नाही", "bn": "ব্যাংক অ্যাকাউন্ট নেই", "ml": "ബാങ്ക് അക്കൗണ്ട് ഇല്ല"}.get(language, "no bank account"))
    return ", ".join(bit for bit in bits if bit)


def question_for(field: str | None, language: str) -> str:
    if not field:
        return ""
    return say(QUESTION_KEY.get(field, "invite"), language)


def strip_tags(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).replace("  ", " ").strip()
