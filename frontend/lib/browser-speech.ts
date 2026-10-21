/** How long one health check may stay open. Render's free tier can take ~35s to wake. */
export const HEALTH_ABORT_MS = 45000;

/** Ping often enough that an open desk keeps the free instance from sleeping. */
export const HEALTH_KEEPALIVE_MS = 90000;

export const HEALTH_RETRY_MS = 2000;

/** Same tags as BROWSER_LANG in phrases.ts. Auto and Hinglish use Hindi. */
const RECOGNITION_LANG: Record<string, string> = {
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

/** SpeechRecognition language for the desk picker. */
export function recognitionLang(language: string): string {
  if (!language || language === "auto") return "hi-IN";
  return RECOGNITION_LANG[language] || "hi-IN";
}

export function rankedVoice<T extends { name: string; lang: string }>(voices: T[], lang: string): T | null {
  const want = (lang || "hi-IN").toLowerCase();
  const prefix = want.slice(0, 2);
  const exact = voices.filter((voice) => voice.lang.toLowerCase() === want);
  const same = exact.length ? exact : voices.filter((voice) => voice.lang.toLowerCase().startsWith(prefix));
  return same.find((voice) => /female|woman|natural/i.test(voice.name)) || same[0] || null;
}

/** Backup timer if the device voice never fires onend. Short, so a stall does not hold the turn. */
export function deviceSpeechTimeout(text: string): number {
  const length = text.trim().length;
  return Math.min(9000, 400 + length * 35);
}
