"use client";

import { SCHEMES, STEPS } from "@/lib/catalog";
import { LANGUAGES } from "@/lib/phrases";

export function Landing({
  language,
  onLanguage,
  onStart,
  onDemo,
  speech,
}: {
  language: string;
  onLanguage: (id: string) => void;
  onStart: () => void;
  onDemo: () => void;
  speech: "gnani" | "mock" | null;
}) {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-6 pt-8 sm:px-6 sm:pt-14">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold tracking-[0.18em] text-[#0e6b45] uppercase">जनवाणी</p>
        <h1 className="font-display mt-3 text-[2.6rem] leading-[1.02] text-[#1a1612] sm:text-7xl">
          Speak. Match. Leave with a slip.
        </h1>
        <p className="mt-5 max-w-2xl text-xl leading-snug text-[#3c342c] sm:text-2xl">
          Speak in your language, get matched to welfare schemes, and leave with a ready-to-submit slip.
        </p>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-[#5c5146]">
          A citizen talks. JanVaani fills the scheme form, checks 19 government schemes, and prints a CSC Ready Slip with a QR code.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
          <button type="button" className="cta" onClick={onStart}>
            Start talking
          </button>
          <button type="button" className="cta cta-quiet" onClick={onDemo}>
            Play 60-second demo
          </button>
        </div>
        <p className="mt-5 text-sm font-semibold tracking-wide text-[#0e6b45]">
          Powered by Gnani.ai
          <span className="ml-2 font-normal text-[#5c5146]">
            {speech === "gnani" ? "Prisma listens · Timbre speaks · voice Shivani" : "Prisma STT · Timbre TTS · Shivani"}
          </span>
        </p>
      </div>

      <ol className="mt-12 grid gap-3 sm:grid-cols-3">
        {STEPS.map((step) => (
          <li key={step.n} className="rounded-2xl border border-[#e4d7c4] bg-[#fffdf8] p-5">
            <p className="font-display text-sm text-[#c47a2c]">{step.n}</p>
            <h2 className="font-display mt-2 text-3xl text-[#1a1612]">{step.title}</h2>
            <p className="mt-2 text-base leading-relaxed text-[#3c342c]">{step.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-10">
        <h2 className="font-display text-3xl text-[#1a1612]">Languages</h2>
        <p className="mt-1 text-base text-[#5c5146]">Pick one, or leave Auto and JanVaani will follow you.</p>
        <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Language">
          {LANGUAGES.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={language === item.id}
              className={`lang-pill ${language === item.id ? "lang-pill-on" : ""}`}
              onClick={() => onLanguage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-10">
        <h2 className="font-display text-3xl text-[#1a1612]">19 schemes</h2>
        <p className="mt-1 max-w-2xl text-base text-[#5c5146]">
          National schemes, plus Gruha Lakshmi, Ladki Bahin, Rythu Bharosa, and Lakshmir Bhandar. A rule decides. The list on the call shows why.
        </p>
        <ul className="mt-4 flex flex-wrap gap-2">
          {SCHEMES.map((scheme) => (
            <li key={scheme.name} className="rounded-full border border-[#e4d7c4] bg-[#fffdf8] px-3 py-1.5 text-sm text-[#1a1612]">
              <span className="font-semibold">{scheme.name}</span>
              <span className="text-[#5c5146]"> · {scheme.who}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
