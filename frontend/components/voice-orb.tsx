"use client";

import type { Phase } from "@/lib/use-call";

const LABEL: Record<Phase, string> = {
  idle: "Start talking",
  connecting: "Connecting",
  listening: "End call",
  thinking: "End call",
  speaking: "End call",
  ended: "Call again",
  error: "Try again",
};

export function VoiceOrb({
  phase,
  level,
  onPress,
  disabled,
}: {
  phase: Phase;
  level: number;
  onPress: () => void;
  disabled?: boolean;
}) {
  const live = phase === "listening" || phase === "speaking" || phase === "thinking" || phase === "connecting";
  const energy = Math.max(0.12, Math.min(1, level));
  return (
    <button
      type="button"
      className="orb-hit"
      data-phase={phase}
      style={{ ["--level" as string]: String(energy) }}
      onClick={onPress}
      disabled={disabled}
      aria-pressed={live}
    >
      <span className="orb-ring" aria-hidden="true" />
      <span className="orb-ring delay" aria-hidden="true" />
      <span className="orb-face" aria-hidden="true">
        <span className="orb-bars">
          <i />
          <i />
          <i />
          <i />
          <i />
        </span>
        <span className="orb-label">{LABEL[phase]}</span>
      </span>
    </button>
  );
}
