"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState } from "react";
import { Landing } from "@/components/landing";
import { VoiceOrb } from "@/components/voice-orb";
import { Button } from "@/components/ui/button";
import { connectionLabel, wakeCaption } from "@/lib/line-status";
import { LANGUAGES, PHRASES } from "@/lib/phrases";
import { useCall, type SchemeMatch } from "@/lib/use-call";

const PENDING: Record<string, string> = {
  district: "Your district",
  occupation: "Your work",
  land_acres: "Land, in acres",
  age: "Your age",
  gender: "Woman or man",
  bpl: "BPL or ration card",
  crop: "This season's crop",
  area: "Village or town",
  housing: "Kutcha or pucca house",
  lpg: "Gas cylinder",
  bank_account: "Bank account",
  name_match: "Name on Aadhaar and ration card",
  mobile_linked: "Mobile linked to Aadhaar",
  senior_age: "An elder at home",
  widow: "Widow pension",
  pregnant: "Pregnancy",
  annual_income: "Family income",
};

const FORM = [
  ["district", "District"],
  ["state_name", "State"],
  ["occupation", "Work"],
  ["land_acres", "Land"],
  ["crop", "Crop"],
  ["age", "Age"],
  ["gender", "Gender"],
  ["bpl", "BPL"],
  ["senior_age", "Elder at home"],
  ["bank_account", "Bank account"],
  ["name_match", "Names match"],
  ["mobile_linked", "Mobile linked"],
] as const;

const PHASE_LINE: Record<string, string> = {
  idle: "Tap the orb, or play the demo. Talk as you would at a CSC counter.",
  connecting: "Opening the line. The server may still be waking.",
  listening: "Listening. Speak, or tap a phrase.",
  thinking: "Writing that down…",
  speaking: "JanVaani is speaking. Talk over her to interrupt.",
  ended: "Call ended. The slip stays on this page.",
  error: "The line stopped. You can start it again.",
};

export function Desk() {
  const [language, setLanguage] = useState("auto");
  const [draft, setDraft] = useState("");
  const [showOthers, setShowOthers] = useState(false);
  const [slipError, setSlipError] = useState<string | null>(null);
  const [pulse, setPulse] = useState<string[]>([]);
  const call = useCall(language);
  const reduce = useReducedMotion();
  const seen = useRef(new Map<string, string>());
  const transcriptEnd = useRef<HTMLDivElement>(null);
  const inCall = call.phase === "connecting" || call.phase === "listening" || call.phase === "thinking" || call.phase === "speaking";
  const established = call.phase === "listening" || call.phase === "thinking" || call.phase === "speaking";
  const statusLabel = connectionLabel({ phase: call.phase, demo: call.demo, line: call.line });
  const statusTone =
    statusLabel === "Live" || statusLabel === "Demo mode"
      ? "status-live"
      : statusLabel === "Line is down" || statusLabel === "Line dropped"
        ? "status-down"
        : statusLabel === "Ready"
          ? "status-idle"
          : "status-wait";
  const textFallback = call.mic === "denied" || call.mic === "missing";
  const state = call.callState;
  const langLabel = LANGUAGES.find((item) => item.id === (state?.language || language))?.label ?? "Auto";

  const qualify = state?.matches.filter((item) => item.status === "qualify") ?? [];
  const likely = state?.matches.filter((item) => item.status === "likely") ?? [];
  const needs = state?.matches.filter((item) => item.status === "need_answer") ?? [];
  const skipped = state?.matches.filter((item) => item.status === "not_eligible" || item.status === "insufficient") ?? [];
  const rows = useMemo(() => new Map((state?.rows ?? []).map((row) => [row.field, row])), [state]);
  const extra = (state?.rows ?? []).filter((row) => !FORM.some((item) => item[0] === row.field));

  useEffect(() => {
    const next = new Map<string, string>();
    const changed: string[] = [];
    for (const row of state?.rows ?? []) {
      next.set(row.field, row.value);
      if (seen.current.get(row.field) !== row.value) changed.push(row.field);
    }
    seen.current = next;
    if (!changed.length) return;
    setPulse(changed);
    const timer = window.setTimeout(() => setPulse([]), 1400);
    return () => window.clearTimeout(timer);
  }, [state]);

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
  }, [call.captions, reduce]);

  function chooseLanguage(id: string) {
    setLanguage(id);
    call.setLiveLanguage(id);
  }

  function begin(demo: boolean) {
    if (call.line !== "ready") return;
    // Start the call in this tap, before scrolling. getUserMedia and speech
    // recognition have to run before the gesture ends.
    if (!(established && !demo)) void call.start({ demo });
    document.getElementById("desk")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  function onOrb() {
    if (inCall) call.hangup();
    else if (call.line === "ready") void call.start();
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-[#e4d7c4]/80 bg-[#f6f1e7]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-[#0e6b45]">जनवाणी</p>
            <p className="font-display truncate text-2xl leading-none text-[#1a1612]">JanVaani</p>
          </div>
          <p className="hidden text-sm font-semibold text-[#0e6b45] md:block">Powered by Gnani.ai</p>
          <div className="flex items-center gap-2">
            <span className={`status-pill ${statusTone}`} role="status">
              {statusLabel}
            </span>
            <button type="button" className="cta cta-small" onClick={() => begin(false)} disabled={call.line !== "ready"}>
              Start talking
            </button>
          </div>
        </div>
      </header>

      <div className="bg-[#9d2c2c] px-4 py-2 text-center text-sm text-white">
        Practice data only. Do not say a real Aadhaar, PAN, or phone number.
      </div>

      {call.line !== "ready" ? (
        <div className="border-b border-[#f0ddb4] bg-[#fff4df] px-4 py-3">
          <div className="mx-auto flex max-w-6xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#8a4e12]">
                {call.line === "down" ? "Still waking the line…" : "Waking up the line…"}
              </p>
              <p className="mt-0.5 text-sm leading-relaxed text-[#5c5146]">{wakeCaption(call.wakeProgress, call.line)}</p>
            </div>
            <div className="w-full sm:w-48 sm:shrink-0">
              <div
                role="progressbar"
                aria-label="Waking up the line"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={call.wakeProgress}
                className="h-2 overflow-hidden rounded-full bg-white"
              >
                <div className="h-full rounded-full bg-[#e08a2c]" style={{ width: `${call.wakeProgress}%` }} />
              </div>
              <p className="mt-1 text-right text-xs font-semibold text-[#8a4e12]">{call.wakeProgress}%</p>
            </div>
          </div>
        </div>
      ) : null}

      {call.line === "ready" && call.health?.speech === "mock" ? (
        <div className="border-b border-[#f0ddb4] bg-[#fff4df] px-4 py-3" role="status">
          <div className="mx-auto max-w-6xl">
            <p className="text-sm font-semibold text-[#8a4e12]">Mock mode</p>
            <p className="mt-0.5 text-sm leading-relaxed text-[#3c342c]">
              No Gnani key is set, so this browser listens and speaks. Scheme matches still follow the fixed rules, not a language model.
              {call.speechBlock ? ` ${call.speechBlock}` : " Speech and synthesis stay off until a key is set: /api/stt and /api/tts return 409."}
            </p>
          </div>
        </div>
      ) : null}

      {call.line === "ready" && call.phase === "idle" && call.greetingWarm ? (
        <div className="border-b border-[#d7eadf] bg-[#eef6f1] px-4 py-2" role="status">
          <p className="mx-auto max-w-6xl text-sm text-[#0e6b45]">Greeting is ready. The first hello should start quickly.</p>
        </div>
      ) : null}

      {call.demo ? (
        <div className="border-b border-[#d7e4f5] bg-[#eef4fb] px-4 py-3" role="status">
          <div className="mx-auto max-w-6xl">
            <p className="text-sm font-semibold text-[#1d4e89]">Demo mode</p>
            <p className="mt-0.5 text-sm leading-relaxed text-[#3c342c]">
              A practice Kolar household speaks for you. The microphone stays off. You can still type a line.
            </p>
          </div>
        </div>
      ) : null}

      <Landing
        language={language}
        onLanguage={chooseLanguage}
        onStart={() => begin(false)}
        onDemo={() => begin(true)}
        speech={call.health?.speech ?? null}
        canStart={call.line === "ready"}
      />

      <main id="desk" className="scroll-mt-20 mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(300px,420px)_1fr]">
        <section aria-label="Call" className="lg:sticky lg:top-20 lg:self-start">
          <div className="rounded-3xl bg-[#10241c] p-5 text-[#f6f1e7] shadow-[0_20px_50px_rgba(16,36,28,0.18)] sm:p-6">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold tracking-[0.16em] text-[#e7c9a4] uppercase">The line</p>
                <p className="mt-1 text-base text-[#f6f1e7]/80">
                  {call.browserEar && call.phase === "listening"
                    ? "Listening in this browser. Speak, or tap a phrase."
                    : PHASE_LINE[call.phase]}
                </p>
              </div>
              <p className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold tracking-wide">
                {call.health?.speech === "gnani" ? `Shivani · Gnani` : "Practice voice"}
              </p>
            </div>

            <div className="mt-2 flex justify-center">
              <VoiceOrb phase={call.phase} level={call.level} onPress={onOrb} disabled={!inCall && call.line !== "ready"} />
            </div>

            <p className="text-center text-sm text-[#e7c9a4]">
              {call.demo ? "Demo · Kolar farmer" : langLabel}
              {state?.language && language === "auto" ? " · detected" : ""}
            </p>

            {call.phase === "speaking" ? (
              <button type="button" className="mt-3 h-12 w-full rounded-full bg-white/10 text-base font-semibold" onClick={call.barge}>
                रुकिए — I’ll listen
              </button>
            ) : null}

            <div className="mt-4 max-h-72 space-y-2 overflow-y-auto pr-1" aria-live="polite">
              {call.captions.length === 0 ? (
                <p className="rounded-2xl bg-white/5 px-4 py-3 text-base text-[#f6f1e7]/75">
                  The line is quiet. Start talking, or play the demo.
                </p>
              ) : (
                <AnimatePresence initial={false}>
                  {call.captions.map((line) => (
                    <motion.p
                      key={line.id}
                      layout
                      initial={reduce ? false : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.28 }}
                      className={`max-w-[95%] rounded-2xl px-4 py-2.5 text-base leading-snug ${
                        line.role === "user" ? "ml-auto bg-[#1f8f5d] text-white" : "bg-white/10 text-[#f6f1e7]"
                      } ${line.filler ? "italic text-[#e7c9a4]" : ""}`}
                    >
                      <span className="mb-0.5 block text-[10px] font-semibold tracking-[0.14em] uppercase opacity-70">
                        {line.role === "user" ? "You" : "JanVaani"}
                      </span>
                      {line.text}
                    </motion.p>
                  ))}
                </AnimatePresence>
              )}
              <div ref={transcriptEnd} />
            </div>

            {state?.pending ? (
              <p className="mt-3 text-sm text-[#e7c9a4]">Asking: {PENDING[state.pending] || state.pending}</p>
            ) : null}
            {call.mic === "denied" ? (
              <div className="mt-3 whitespace-normal break-words rounded-2xl bg-white/10 p-4 text-sm leading-relaxed text-[#f6f1e7]">
                <p>
                  The browser blocked the microphone. Allow the mic for this site in the address bar, then tap Try the microphone again. You can also type below, or tap a phrase. JanVaani still answers.
                </p>
                <button
                  type="button"
                  className="mt-3 h-11 rounded-full bg-[#f6f1e7] px-4 text-sm font-semibold text-[#10241c]"
                  onClick={() => void call.enableMic()}
                >
                  Try the microphone again
                </button>
              </div>
            ) : null}
            {call.mic === "missing" ? (
              <div className="mt-3 whitespace-normal break-words rounded-2xl bg-white/10 p-4 text-sm leading-relaxed text-[#f6f1e7]">
                <p>This browser has no microphone to use. Type what you would say, or tap a phrase. JanVaani still answers.</p>
              </div>
            ) : null}
            {call.mic === "skipped" && call.micNote ? (
              <p className="mt-3 whitespace-normal break-words text-sm leading-relaxed text-[#f0c7a2]">{call.micNote}</p>
            ) : null}
            {call.error ? <p className="mt-3 whitespace-normal break-words text-sm leading-relaxed text-[#ffb4a8]">{call.error}</p> : null}

            <div className="mt-4 flex flex-wrap gap-2">
              {PHRASES.map((phrase) => (
                <button
                  key={phrase.label}
                  type="button"
                  className="rounded-full bg-white/10 px-3 py-2 text-sm font-semibold disabled:opacity-40"
                  disabled={!inCall}
                  onClick={() => call.sendText(phrase.text, "language" in phrase ? phrase.language : undefined)}
                >
                  {phrase.label}
                </button>
              ))}
            </div>

            <form
              className="mt-3 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!draft.trim()) return;
                call.sendText(draft.trim());
                setDraft("");
              }}
            >
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                disabled={!inCall}
                placeholder={textFallback ? "Type here — the microphone is off" : "Or type what you would say"}
                className="h-12 min-w-0 flex-1 rounded-full border border-white/15 bg-white/5 px-4 text-base text-white outline-none placeholder:text-white/40 focus-visible:ring-2 focus-visible:ring-[#e7c9a4] disabled:opacity-40"
                aria-label="Type what you would say"
              />
              <button
                type="submit"
                className="h-12 rounded-full bg-[#f6f1e7] px-4 text-base font-semibold text-[#10241c] disabled:opacity-40"
                disabled={!inCall || !draft.trim()}
              >
                Send
              </button>
            </form>
          </div>
          <div className="mt-3 flex flex-wrap gap-2 px-1" role="group" aria-label="Language on this call">
            {LANGUAGES.map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={language === item.id}
                className={`lang-pill ${language === item.id ? "lang-pill-on" : ""}`}
                onClick={() => chooseLanguage(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-6" aria-label="Form, schemes, and slip">
          <div>
            <h2 className="font-display text-3xl text-[#1a1612]">The form</h2>
            <p className="mt-1 text-base text-[#5c5146]">Fields fill in as she hears them. Empty ones are still to ask.</p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {FORM.map(([field, label]) => {
              const row = rows.get(field);
              const fresh = pulse.includes(field);
              return (
                <motion.div
                  key={field}
                  layout
                  animate={fresh && !reduce ? { backgroundColor: ["#fff4df", "#fffdf8"] } : undefined}
                  transition={{ duration: 1.1 }}
                  className={`rounded-2xl border px-3 py-2 ${row ? "border-[#cfe4d6] bg-[#fffdf8]" : "border-dashed border-[#e4d7c4] bg-transparent"}`}
                >
                  <p className="text-[11px] font-semibold tracking-wide text-[#5c5146] uppercase">{label}</p>
                  <p className={`mt-0.5 truncate text-lg font-semibold ${row ? "text-[#1a1612]" : "text-[#b7ab9c]"}`}>
                    {row?.value || "—"}
                  </p>
                </motion.div>
              );
            })}
            <AnimatePresence initial={false}>
              {extra.map((row) => (
                <motion.div
                  key={row.field}
                  initial={reduce ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-2xl border border-[#cfe4d6] bg-[#fffdf8] px-3 py-2"
                >
                  <p className="text-[11px] font-semibold tracking-wide text-[#5c5146] uppercase">{row.label}</p>
                  <p className="mt-0.5 text-lg font-semibold">{row.value}</p>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          <div>
            <h2 className="font-display text-3xl text-[#1a1612]">Schemes for this house</h2>
            <p className="mt-1 text-base text-[#5c5146]">A fixed rule decides. Each card says why.</p>
          </div>

          {!state || state.user_turns === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#e4d7c4] px-4 py-8 text-lg text-[#5c5146]">
              Nothing matched yet. On the call, say your district, your work, your age, and who is at home.
            </div>
          ) : (
            <>
              <div className="grid gap-3">
                <AnimatePresence initial={false}>
                  {qualify.map((item) => (
                    <SchemeCard key={item.id} item={item} tone="apply" reduce={Boolean(reduce)} />
                  ))}
                  {likely.map((item) => (
                    <SchemeCard key={item.id} item={item} tone="check" reduce={Boolean(reduce)} />
                  ))}
                </AnimatePresence>
                {qualify.length + likely.length === 0 ? (
                  <div className="rounded-2xl border border-[#e4d7c4] bg-[#fffdf8] px-4 py-4 text-base">
                    No scheme is confirmed from what we have heard.
                  </div>
                ) : null}
              </div>
              {needs.length > 0 ? (
                <div>
                  <h3 className="mb-2 text-lg font-semibold">One answer away</h3>
                  <div className="grid gap-2">
                    {needs.slice(0, 4).map((item) => (
                      <SchemeCard key={item.id} item={item} tone="need" reduce={Boolean(reduce)} />
                    ))}
                  </div>
                </div>
              ) : null}
              <button
                type="button"
                className="h-11 self-start text-base font-semibold text-[#0e6b45]"
                onClick={() => setShowOthers((value) => !value)}
              >
                {showOthers ? "Hide" : "Show"} schemes that do not fit ({skipped.length})
              </button>
              {showOthers ? (
                <ul className="grid gap-1 text-sm text-[#5c5146]">
                  {skipped.map((item) => (
                    <li key={item.id}>
                      {item.name}: {item.reasons[0] || item.status}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          )}

          <Slip
            state={state}
            ready={state?.slip === "ready"}
            reduce={Boolean(reduce)}
            copied={call.copied}
            slipError={slipError}
            onCopy={() => void call.copyShare()}
            onPdf={() => {
              if (!state) return;
              setSlipError(null);
              void fetch(`${call.apiBase}/api/slip`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(state),
              })
                .then(async (response) => {
                  if (!response.ok) throw new Error("slip");
                  const blob = await response.blob();
                  const url = URL.createObjectURL(blob);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = `${state.ref || "janvaani"}.pdf`;
                  link.click();
                  URL.revokeObjectURL(url);
                })
                .catch(() => setSlipError("The slip could not be printed. Try the call again."));
            }}
          />
        </section>
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-12 text-sm text-[#5c5146] sm:px-6">
        Built for the Great Indian AI Internship Challenge. Powered by Gnani.ai — Prisma speech-to-text and Timbre speech. Eligibility is a rule, not a guess.
      </footer>
    </div>
  );
}

function SchemeCard({ item, tone, reduce }: { item: SchemeMatch; tone: "apply" | "check" | "need"; reduce: boolean }) {
  const label = tone === "apply" ? "Apply" : tone === "check" ? "Check at CSC" : "Need one answer";
  const toneClass = tone === "apply" ? "bg-[#e7f6ee] border-[#b7e0c8]" : tone === "check" ? "bg-[#fff4df] border-[#f0ddb4]" : "bg-[#fffdf8] border-[#e4d7c4]";
  return (
    <motion.article
      layout
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={`rounded-2xl border p-4 ${toneClass}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl font-semibold">{item.name}</h3>
        <span className="text-xs font-semibold tracking-wide uppercase">{label}</span>
      </div>
      <p className="mt-1 text-base">{item.reasons[0]}</p>
      {item.reasons[1] ? <p className="mt-1 text-sm text-[#5c5146]">{item.reasons[1]}</p> : null}
      <p className="mt-1 text-sm text-[#5c5146]">
        {item.authority} · {item.portal}
      </p>
    </motion.article>
  );
}

function Slip({
  state,
  ready,
  reduce,
  copied,
  slipError,
  onCopy,
  onPdf,
}: {
  state: ReturnType<typeof useCall>["callState"];
  ready: boolean;
  reduce: boolean;
  copied: boolean;
  slipError: string | null;
  onCopy: () => void;
  onPdf: () => void;
}) {
  return (
    <motion.div
      id="slip"
      layout
      animate={ready && !reduce ? { scale: [0.985, 1] } : undefined}
      className={`rounded-3xl border bg-[#fffdf8] p-5 ${ready ? "border-[#e08a2c] shadow-[0_12px_40px_rgba(224,138,44,0.18)]" : "border-[#e4d7c4]"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-3xl text-[#1a1612]">Ready Slip</h2>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${ready ? "bg-[#e08a2c] text-white" : "border border-[#e4d7c4]"}`}>
          {ready ? "Ready for the counter" : state?.slip === "draft" ? "Draft" : "Not filled"}
        </span>
      </div>
      <AnimatePresence>
        {ready ? (
          <motion.p
            initial={reduce ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 text-lg font-semibold text-[#8a4e12]"
          >
            The slip is ready. Download the PDF — it carries a QR code for the counter.
          </motion.p>
        ) : null}
      </AnimatePresence>
      <p className="mt-3 text-base">{state?.ref || "The slip gets a practice reference when you call."}</p>
      {state?.fix_first?.length ? (
        <div className="mt-3 rounded-2xl bg-[#ffd9cc] p-4 text-[#6d2418]">
          <p className="text-lg font-semibold">Fix this first</p>
          <ul className="mt-2 grid gap-2">
            {state.fix_first.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="mt-4">
        <p className="text-sm font-semibold tracking-wide text-[#5c5146] uppercase">Papers</p>
        {state?.documents?.length ? (
          <ul className="mt-1 grid gap-1 text-base">
            {state.documents.map((doc) => (
              <li key={doc}>{doc}</li>
            ))}
          </ul>
        ) : (
          <p className="text-base text-[#5c5146]">The list appears with the schemes.</p>
        )}
      </div>
      <p className="mt-3 text-base leading-relaxed">
        {state?.csc || "The nearest CSC note appears once a place is known. Until then, ask the gram panchayat for the Common Service Centre."}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="button" className="h-12 px-4 text-base" disabled={!state} onClick={onPdf}>
          Download PDF
        </Button>
        <Button type="button" variant="secondary" className="h-12 px-4 text-base" disabled={!state} onClick={onCopy}>
          {copied ? "Copied" : "Copy SMS text"}
        </Button>
        <Button type="button" variant="outline" className="h-12 px-4 text-base" onClick={() => window.print()}>
          Print
        </Button>
      </div>
      {slipError ? <p className="mt-2 text-sm text-[#9d2c2c]">{slipError}</p> : null}
      {state?.share_text ? (
        <pre className="mt-4 whitespace-pre-wrap rounded-2xl bg-[#f6f1e7] p-4 text-sm leading-relaxed">{state.share_text}</pre>
      ) : null}
    </motion.div>
  );
}
