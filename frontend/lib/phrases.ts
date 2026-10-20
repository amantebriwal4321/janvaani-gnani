export const LANGUAGES = [
  { id: "auto", label: "Auto" },
  { id: "hi", label: "हिन्दी" },
  { id: "hi-en", label: "Hinglish" },
  { id: "en", label: "English" },
  { id: "kn", label: "ಕನ್ನಡ" },
  { id: "te", label: "తెలుగు" },
  { id: "ta", label: "தமிழ்" },
  { id: "mr", label: "मराठी" },
  { id: "bn", label: "বাংলা" },
  { id: "ml", label: "മലയാളം" },
] as const;

export const BROWSER_LANG: Record<string, string> = {
  hi: "hi-IN",
  "hi-en": "hi-IN",
  en: "en-IN",
  kn: "kn-IN",
  te: "te-IN",
  ta: "ta-IN",
  mr: "mr-IN",
  bn: "bn-IN",
  ml: "ml-IN",
};

export const PHRASES = [
  {
    label: "Kolar farmer",
    language: "hi",
    text: "Main Kolar ke paas ek gaon se hoon, do acre mein tamatar ugata hoon, umar pentalees saal. Is baar baarish se fasal kharab ho gayi. BPL card hai, pitaji bahattar saal ke hain.",
  },
  {
    label: "Mysuru tailor",
    language: "kn",
    text: "ನಾನು ಮೈಸೂರಿನ ಹಳ್ಳಿಯಿಂದ. ನಾನು ದರ್ಜಿ. ವಯಸ್ಸು 38. ನಾನು ಹೆಂಗಸು.",
  },
  {
    label: "Nagpur thela",
    language: "hi-en",
    text: "Main Nagpur se hoon, thela lagata hoon, umar tees saal, mard hoon, BPL nahi hai, bank account nahi hai.",
  },
  { label: "Haan", text: "haan" },
  { label: "Naam alag", text: "nahi, naam alag likha hai" },
];
