"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export function Desk() {
  const [language, setLanguage] = useState("auto");
  const [draft, setDraft] = useState("");
  const [showOthers, setShowOthers] = useState(false);
  const [slipError, setSlipError] = useState<string | null>(null);
  const call = useCall(language);
  const inCall = call.phase === "connecting" || call.phase === "listening" || call.phase === "speaking";
  const state = call.callState;
  const qualify = state?.matches.filter((item) => item.status === "qualify") ?? [];
  const likely = state?.matches.filter((item) => item.status === "likely") ?? [];
  const needs = state?.matches.filter((item) => item.status === "need_answer") ?? [];
  const skipped = state?.matches.filter((item) => item.status === "not_eligible" || item.status === "insufficient") ?? [];
  const assistant = [...call.captions].reverse().find((line) => line.role === "assistant");
  const caller = [...call.captions].reverse().find((line) => line.role === "user");

  function chooseLanguage(id: string) {
    setLanguage(id);
    call.setLiveLanguage(id);
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-[#fffaf3]/90">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-5 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm font-semibold tracking-wide text-[#0c6b45]">जनवाणी</p>
              <h1 className="font-display text-4xl leading-none text-[#1c1712] sm:text-5xl">JanVaani</h1>
              <p className="mt-2 max-w-xl text-lg text-[#3d342b]">
                Speak in your language. The welfare form fills itself, and you leave with a CSC slip.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={call.health?.speech === "gnani" ? "default" : "secondary"} className="h-7 px-3 text-sm">
                {call.health?.speech === "gnani" ? `Gnani ${call.health.voice}` : "Mock voice"}
              </Badge>
              <Badge variant="outline" className="h-7 px-3 text-sm">
                {call.health ? `${call.health.schemes} schemes` : "8 kHz line"}
              </Badge>
            </div>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Language">
            {LANGUAGES.map((item) => (
              <Button
                key={item.id}
                type="button"
                variant={language === item.id ? "default" : "outline"}
                className="h-11 min-w-16 px-3 text-base"
                onClick={() => chooseLanguage(item.id)}
              >
                {item.label}
              </Button>
            ))}
          </div>
        </div>
      </header>

      <div className="bg-[#9d2c2c] px-4 py-2 text-center text-sm text-white sm:text-base">
        Practice data only. Do not say a real Aadhaar, PAN, or phone number.
      </div>

      <main className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(320px,420px)_1fr]">
        <section aria-label="Call">
          <Card className="sticky top-4">
            <CardHeader>
              <CardTitle className="font-display text-2xl">The line</CardTitle>
              <p className="text-base text-muted-foreground">
                {call.phase === "idle" && "Tap the green button. Talk as you would at a CSC counter."}
                {call.phase === "connecting" && "Connecting the 8 kHz line…"}
                {call.phase === "listening" && "Listening. Speak, or tap a phrase."}
                {call.phase === "speaking" && "JanVaani is speaking. Talk over her to interrupt."}
                {call.phase === "ended" && "Call ended. The slip stays on this page."}
                {call.phase === "error" && "The line stopped."}
              </p>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-center py-2">
                {inCall ? (
                  <div className="relative flex h-36 w-36 items-center justify-center">
                    {call.phase === "speaking" || call.phase === "listening" ? (
                      <span className="ring-live absolute inset-0 rounded-full bg-[#0c6b45]/30" />
                    ) : null}
                    <button
                      type="button"
                      onClick={call.hangup}
                      className="relative z-10 flex h-28 w-28 items-center justify-center rounded-full bg-[#9d2c2c] text-lg font-semibold text-white shadow-md"
                    >
                      End
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => void call.start()}
                    className="flex h-36 w-36 items-center justify-center rounded-full bg-[#0c6b45] text-xl font-semibold text-white shadow-lg"
                  >
                    Call
                  </button>
                )}
              </div>

              {call.phase === "speaking" ? (
                <Button type="button" className="h-14 text-lg" onClick={call.barge}>
                  रुकिए — I will listen
                </Button>
              ) : null}

              <div className="min-h-36 rounded-xl bg-[#1c1712] p-4 text-[#fffaf3]" aria-live="polite">
                <p className="text-xs uppercase tracking-wider text-[#e7c9a4]">JanVaani</p>
                <p className="mt-1 text-xl leading-snug" lang={state?.language || "hi"}>
                  {assistant?.text || "The line is quiet. Call, then speak in your own words."}
                </p>
                {caller ? (
                  <p className="mt-3 text-base text-[#f3ecdf]/80">
                    <span className="text-[#e7c9a4]">You. </span>
                    {caller.text}
                  </p>
                ) : null}
                {state?.pending ? (
                  <p className="mt-3 text-sm text-[#e7c9a4]">Asking: {PENDING[state.pending] || state.pending}</p>
                ) : null}
              </div>

              {call.micNote ? <p className="text-sm text-[#9d2c2c]">{call.micNote}</p> : null}
              {call.error ? <p className="text-sm text-[#9d2c2c]">{call.error}</p> : null}
              {call.health?.speech === "mock" ? (
                <p className="text-sm text-muted-foreground">
                  Mock ears cannot hear the microphone yet. Tap a phrase or type. Set GNANI_API_KEY and the same call uses Prisma and Timbre.
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Live on Gnani Prisma and Timbre, 8 kHz, the same audio a phone line would carry.
                </p>
              )}

              <div className="flex flex-wrap gap-2">
                {PHRASES.map((phrase) => (
                  <Button
                    key={phrase.label}
                    type="button"
                    variant="secondary"
                    className="h-12 px-3 text-base"
                    disabled={!inCall}
                    onClick={() => call.sendText(phrase.text, "language" in phrase ? phrase.language : undefined)}
                  >
                    {phrase.label}
                  </Button>
                ))}
              </div>

              <form
                className="flex gap-2"
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
                  placeholder="Or type what you would say"
                  className="h-12 flex-1 rounded-lg border border-input bg-white px-3 text-base outline-none focus-visible:ring-3 focus-visible:ring-ring/40 disabled:opacity-50"
                  aria-label="Type what you would say"
                />
                <Button type="submit" className="h-12 px-4 text-base" disabled={!inCall || !draft.trim()}>
                  Send
                </Button>
              </form>
            </CardContent>
          </Card>
        </section>

        <section className="flex flex-col gap-6" aria-label="Schemes and slip">
          <div>
            <h2 className="font-display text-3xl">Schemes for this house</h2>
            <p className="mt-1 text-base text-muted-foreground">
              A fixed rule decides. The voice model never says you qualify on its own.
            </p>
          </div>

          {!state || state.user_turns === 0 ? (
            <Card>
              <CardContent className="py-8 text-lg">
                Nothing filled yet. On the call, say your district, your work, your age, and who is at home.
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid gap-3">
                {qualify.map((item) => (
                  <SchemeCard key={item.id} item={item} tone="apply" />
                ))}
                {likely.map((item) => (
                  <SchemeCard key={item.id} item={item} tone="check" />
                ))}
                {qualify.length + likely.length === 0 ? (
                  <Card>
                    <CardContent className="text-base">No scheme is confirmed from what we have heard.</CardContent>
                  </Card>
                ) : null}
              </div>

              {needs.length > 0 ? (
                <div>
                  <h3 className="mb-2 text-lg font-semibold">One answer away</h3>
                  <div className="grid gap-2">
                    {needs.slice(0, 4).map((item) => (
                      <SchemeCard key={item.id} item={item} tone="need" />
                    ))}
                  </div>
                </div>
              ) : null}

              <Button type="button" variant="ghost" className="h-11 self-start text-base" onClick={() => setShowOthers((value) => !value)}>
                {showOthers ? "Hide" : "Show"} schemes that do not fit ({skipped.length})
              </Button>
              {showOthers ? (
                <ul className="grid gap-1 text-sm text-muted-foreground">
                  {skipped.map((item) => (
                    <li key={item.id}>
                      {item.name}: {item.reasons[0] || item.status}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="font-display text-2xl">What we wrote down</CardTitle>
            </CardHeader>
            <CardContent>
              {state && state.rows.length > 0 ? (
                <ul className="flex flex-wrap gap-2">
                  {state.rows.map((row) => (
                    <li key={row.field} className="max-w-full rounded-xl bg-secondary px-3 py-2">
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">{row.label}</p>
                      <p className="text-lg font-semibold">{row.value}</p>
                      {row.heard ? <p className="text-sm text-muted-foreground">heard “{row.heard}”</p> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-base text-muted-foreground">Fields show up here with the words that filled them.</p>
              )}
            </CardContent>
          </Card>

          <Card id="slip">
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <CardTitle className="font-display text-2xl">CSC Ready Slip</CardTitle>
                <Badge variant={state?.slip === "ready" ? "default" : "outline"} className="h-7 px-3 text-sm">
                  {state?.slip === "ready" ? "Ready for the counter" : state?.slip === "draft" ? "Draft" : "Not filled"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-base">{state?.ref || "The slip gets a practice reference when you call."}</p>
              {state?.fix_first?.length ? (
                <div className="rounded-xl bg-[#ffd9cc] p-4 text-[#6d2418]">
                  <p className="text-lg font-semibold">Fix this first</p>
                  <ul className="mt-2 grid gap-2">
                    {state.fix_first.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Papers</p>
                {state?.documents?.length ? (
                  <ul className="mt-1 grid gap-1 text-base">
                    {state.documents.map((doc) => (
                      <li key={doc}>{doc}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-base text-muted-foreground">The list appears with the schemes.</p>
                )}
              </div>
              <p className="text-base leading-relaxed">{state?.csc || "The nearest CSC note appears once a place is known. Until then, ask the gram panchayat for the Common Service Centre."}</p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  className="h-12 px-4 text-base"
                  disabled={!state}
                  onClick={() => {
                    if (!state) return;
                    setSlipError(null);
                    void fetch(`${call.apiBase}/api/slip`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify(state),
                    })
                      .then(async (response) => {
                        if (!response.ok) throw new Error("The slip could not be printed.");
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
                >
                  Download PDF
                </Button>
                <Button type="button" variant="secondary" className="h-12 px-4 text-base" disabled={!state} onClick={() => void call.copyShare()}>
                  {call.copied ? "Copied" : "Copy SMS text"}
                </Button>
                <Button type="button" variant="outline" className="h-12 px-4 text-base" onClick={() => window.print()}>
                  Print
                </Button>
              </div>
              {slipError ? <p className="text-sm text-[#9d2c2c]">{slipError}</p> : null}
              {state?.share_text ? (
                <pre className="whitespace-pre-wrap rounded-xl bg-muted p-4 text-sm leading-relaxed">{state.share_text}</pre>
              ) : null}
            </CardContent>
          </Card>
        </section>
      </main>
      <footer className="mx-auto max-w-6xl px-4 pb-10 text-sm text-muted-foreground sm:px-6">
        Built for the Great Indian AI Internship Challenge. Speech is Gnani Prisma and Timbre. Eligibility is a rule, not a guess. A phone number on Exotel or Twilio can use the same 8 kHz line later.
      </footer>
    </div>
  );
}

function SchemeCard({ item, tone }: { item: SchemeMatch; tone: "apply" | "check" | "need" }) {
  const label = tone === "apply" ? "Apply" : tone === "check" ? "Check at CSC" : "Need one answer";
  const toneClass = tone === "apply" ? "bg-[#e5f6ec]" : tone === "check" ? "bg-[#fff1d6]" : "bg-white";
  return (
    <article className={`rounded-xl border border-border p-4 ${toneClass}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl font-semibold">{item.name}</h3>
        <span className="text-sm font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-1 text-base">{item.reasons[0]}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        {item.authority} · {item.portal}
      </p>
    </article>
  );
}
