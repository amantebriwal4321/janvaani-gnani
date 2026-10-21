export type LineState = "waking" | "ready" | "down";

/** How far the wake bar should sit while Render is still asleep. Caps under 100 until health answers. */
export function wakePercent(elapsedMs: number): number {
  const elapsed = Math.max(0, elapsedMs);
  const climbed = Math.round(8 + (elapsed / 42000) * 84);
  return Math.max(8, Math.min(92, climbed));
}

/** Copy under the bar. A cold Render boot often takes about half a minute, so the words keep moving with it. */
export function wakeCaption(progress: number, line: LineState): string {
  if (line === "down") return "Still waking the line. The server is taking longer than usual.";
  if (progress < 30) return "Calling the voice server. Start talking turns on when it answers.";
  if (progress < 70) return "Waking up the line. A cold start often takes about half a minute.";
  return "Almost there. Start talking turns on as soon as the line answers.";
}

export function connectionLabel(input: { phase: string; demo: boolean; line: LineState }): string {
  const onCall =
    input.phase === "connecting" ||
    input.phase === "listening" ||
    input.phase === "thinking" ||
    input.phase === "speaking";
  if (input.demo && onCall) return "Demo mode";
  if (input.phase === "connecting") return input.line === "ready" ? "Connecting" : "Waking up the line…";
  if (input.phase === "listening" || input.phase === "thinking" || input.phase === "speaking") return "Live";
  if (input.line === "waking") return "Waking up the line…";
  if (input.line === "down") return "Line is down";
  if (input.phase === "error") return "Line dropped";
  return "Ready";
}

export function classifyMic(err: unknown): "denied" | "missing" {
  const name = err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
  if (name === "NotFoundError" || name === "NotSupportedError" || name === "NotReadableError") return "missing";
  return "denied";
}
