"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiBase, wsBase } from "./endpoints";
import { BROWSER_LANG } from "./phrases";

export type Phase = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "ended" | "error";

export type ProfileRow = { field: string; label: string; value: string; heard?: string };
export type SchemeMatch = {
  id: string;
  name: string;
  authority: string;
  portal: string;
  status: string;
  reasons: string[];
  missing: string[];
  documents: string[];
  spoken: Record<string, string>;
};
export type CallState = {
  session_id: string;
  ref: string;
  language: string;
  rows: ProfileRow[];
  matches: SchemeMatch[];
  documents: string[];
  fix_first: string[];
  csc: string;
  slip: "early" | "draft" | "ready";
  pending: string | null;
  share_text: string;
  llm: string;
  user_turns: number;
  scheme_count: number;
};

export type Caption = { id: number; role: "user" | "assistant"; text: string; filler?: boolean };

export type Health = {
  ok: boolean;
  speech: "gnani" | "mock";
  tts: string;
  voice: string;
  llm: string;
  schemes: number;
  sample_rate: number;
};

type Player = {
  push: (pcm: ArrayBuffer) => void;
  stop: () => void;
  remaining: () => number;
};

function makePlayer(ctx: AudioContext): Player {
  const gain = ctx.createGain();
  gain.connect(ctx.destination);
  const nodes: AudioBufferSourceNode[] = [];
  let next = 0;
  return {
    push(pcm: ArrayBuffer) {
      const now = ctx.currentTime;
      gain.gain.cancelScheduledValues(now);
      gain.gain.setValueAtTime(1, now);
      const view = new Int16Array(pcm.slice(0));
      const floats = new Float32Array(view.length);
      for (let i = 0; i < view.length; i++) floats[i] = view[i] / 32768;
      const buffer = ctx.createBuffer(1, Math.max(1, floats.length), 8000);
      buffer.copyToChannel(floats, 0);
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(gain);
      if (next < now + 0.02) next = now + 0.04;
      source.start(next);
      next += buffer.duration;
      nodes.push(source);
      source.onended = () => {
        const index = nodes.indexOf(source);
        if (index >= 0) nodes.splice(index, 1);
      };
    },
    stop() {
      const now = ctx.currentTime;
      gain.gain.cancelScheduledValues(now);
      gain.gain.setValueAtTime(Math.max(gain.gain.value, 0.0001), now);
      gain.gain.linearRampToValueAtTime(0.0001, now + 0.07);
      const live = nodes.slice();
      nodes.length = 0;
      next = 0;
      window.setTimeout(() => {
        for (const source of live) {
          try {
            source.stop();
          } catch {
            /* already stopped */
          }
        }
      }, 80);
    },
    remaining() {
      return Math.max(0, next - ctx.currentTime);
    },
  };
}

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis?.getVoices?.() ?? [];
  const prefix = (lang || "hi-IN").slice(0, 2).toLowerCase();
  const same = voices.filter((voice) => voice.lang.toLowerCase().startsWith(prefix));
  return same.find((voice) => /female|woman|natural/i.test(voice.name)) || same[0] || null;
}

export function useCall(language: string) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [callState, setCallState] = useState<CallState | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [micNote, setMicNote] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [level, setLevel] = useState(0.15);
  const [demo, setDemo] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<Player | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const phaseRef = useRef<Phase>("idle");
  const speakTurn = useRef<number | null>(null);
  const speakStarted = useRef(0);
  const hot = useRef(0);
  const captionId = useRef(1);
  const thinkStamp = useRef(0);
  const meterAt = useRef(0);
  const languageRef = useRef(language);
  languageRef.current = language;

  const go = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  useEffect(() => {
    let gone = false;
    fetch(`${apiBase()}/api/health`)
      .then((response) => response.json())
      .then((body) => {
        if (!gone) setHealth(body);
      })
      .catch(() => {
        /* The call button reports a down line. The landing still explains the product. */
      });
    return () => {
      gone = true;
    };
  }, []);

  const stopAudio = useCallback(() => {
    playerRef.current?.stop();
    if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
  }, []);

  const finishSpeak = useCallback((turnId: number | null) => {
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN && turnId != null) {
      socket.send(JSON.stringify({ type: "speak_done", turnId }));
    }
  }, []);

  const speakOnDevice = useCallback(
    (text: string, lang: string, turnId: number) => {
      const clean = text.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
      if (!clean || !window.speechSynthesis) {
        finishSpeak(turnId);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.lang = lang || "hi-IN";
      utterance.rate = 0.96;
      utterance.pitch = 1.04;
      const voice = pickVoice(utterance.lang);
      if (voice) utterance.voice = voice;
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        if (speakTurn.current === turnId) finishSpeak(turnId);
      };
      utterance.onend = done;
      utterance.onerror = done;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      window.setTimeout(done, Math.min(20000, 700 + clean.length * 68));
    },
    [finishSpeak],
  );

  const armThinking = useCallback(() => {
    const stamp = ++thinkStamp.current;
    window.setTimeout(() => {
      if (thinkStamp.current !== stamp) return;
      if (phaseRef.current === "listening" || phaseRef.current === "speaking" || phaseRef.current === "connecting") {
        go("thinking");
      }
    }, 180);
  }, [go]);

  const hangup = useCallback(() => {
    stopAudio();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setLevel(0.15);
    go("ended");
  }, [go, stopAudio]);

  const barge = useCallback(() => {
    hot.current = 0;
    stopAudio();
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "barge_in" }));
    }
    if (phaseRef.current === "speaking" || phaseRef.current === "thinking") go("listening");
  }, [go, stopAudio]);

  const sendText = useCallback(
    (text: string, nextLanguage?: string) => {
      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      if (nextLanguage && nextLanguage !== "auto") {
        socket.send(JSON.stringify({ type: "set_language", language: nextLanguage }));
      }
      armThinking();
      socket.send(JSON.stringify({ type: "utterance", text }));
    },
    [armThinking],
  );

  const start = useCallback(
    async (options?: { demo?: boolean }) => {
      const asDemo = Boolean(options?.demo);
      if (typeof window !== "undefined" && window.speechSynthesis) {
        const unlock = new SpeechSynthesisUtterance(" ");
        unlock.volume = 0;
        window.speechSynthesis.speak(unlock);
      }
      setError(null);
      setMicNote(null);
      setCaptions([]);
      setCopied(false);
      setDemo(asDemo);
      setLevel(0.15);
      stopAudio();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      wsRef.current?.close();
      void ctxRef.current?.close();

      const ctx = new AudioContext();
      ctxRef.current = ctx;
      void ctx.resume();
      playerRef.current = makePlayer(ctx);
      go("connecting");

      const socket = new WebSocket(`${wsBase()}/ws/call`);
      socket.binaryType = "arraybuffer";
      wsRef.current = socket;

      const pushCaption = (role: "user" | "assistant", text: string, filler = false) => {
        const id = captionId.current++;
        setCaptions((current) => {
          const kept = filler ? current.filter((line) => !line.filler) : current.filter((line) => !line.filler);
          return [...kept, { id, role, text, filler }].slice(-16);
        });
      };

      socket.onmessage = (event) => {
        if (typeof event.data !== "string") {
          playerRef.current?.push(event.data as ArrayBuffer);
          return;
        }
        const message = JSON.parse(event.data);
        if (message.type === "ready") {
          setCallState(null);
          setDemo(Boolean(message.demo));
          go("listening");
        } else if (message.type === "status") {
          if (message.phase === "speaking") {
            thinkStamp.current += 1;
            go("speaking");
            speakStarted.current = Date.now();
            speakTurn.current = message.turnId ?? null;
          } else if (message.phase === "thinking") {
            armThinking();
          } else if (message.phase === "listening") {
            if (message.barged) stopAudio();
            if (phaseRef.current !== "thinking") go("listening");
            if (message.barged) go("listening");
          }
        } else if (message.type === "filler") {
          thinkStamp.current += 1;
          go("thinking");
          pushCaption("assistant", message.text, true);
        } else if (message.type === "transcript") {
          pushCaption(message.role, message.text, false);
        } else if (message.type === "state") {
          setCallState(message.state);
        } else if (message.type === "clear") {
          stopAudio();
        } else if (message.type === "speak" && message.audio === "browser") {
          thinkStamp.current += 1;
          go("speaking");
          speakStarted.current = Date.now();
          speakTurn.current = message.turnId ?? null;
          const lang = message.browserLang || BROWSER_LANG[message.language] || "hi-IN";
          speakOnDevice(message.text || "", lang, message.turnId);
        } else if (message.type === "audio_start") {
          thinkStamp.current += 1;
          go("speaking");
          speakStarted.current = Date.now();
          speakTurn.current = message.turnId ?? null;
          playerRef.current?.stop();
        } else if (message.type === "audio_end") {
          const turnId = message.turnId as number;
          const wait = () => {
            const left = playerRef.current?.remaining() ?? 0;
            if (left > 0.08) {
              window.setTimeout(wait, 80);
              return;
            }
            finishSpeak(turnId);
          };
          wait();
        } else if (message.type === "error") {
          setError(message.message);
        }
      };

      socket.onerror = () => {
        setError("The call could not connect. Check that the voice server is running.");
      };
      socket.onclose = () => {
        if (phaseRef.current !== "ended" && phaseRef.current !== "idle" && phaseRef.current !== "error") {
          setError("The line dropped. Your slip is still on this page. Tap Start talking to call again.");
          go("error");
        }
      };

      try {
        await new Promise<void>((resolve, reject) => {
          socket.onopen = () => resolve();
          socket.addEventListener("error", () => reject(new Error("socket")), { once: true });
        });
      } catch {
        setError("The call could not connect. Check that the voice server is running.");
        go("error");
        return;
      }

      if (socket.readyState !== WebSocket.OPEN) {
        go("error");
        return;
      }
      const chosen = languageRef.current;
      if (asDemo) {
        socket.send(JSON.stringify({ type: "demo", language: chosen === "auto" ? "hi" : chosen }));
        setMicNote("Demo mode. A practice household speaks for you, so the microphone stays off.");
        return;
      }
      socket.send(JSON.stringify({ type: "start", language: chosen }));

      try {
        const media = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        });
        streamRef.current = media;
        await ctx.audioWorklet.addModule("/pcm-worklet.js");
        const source = ctx.createMediaStreamSource(media);
        const worklet = new AudioWorkletNode(ctx, "pcm-downsample");
        worklet.port.onmessage = (event) => {
          const frame = event.data;
          if (!frame || frame.type !== "frame") return;
          if (socket.readyState === WebSocket.OPEN) socket.send(frame.pcm.buffer);
          const now = Date.now();
          if (now - meterAt.current > 80) {
            meterAt.current = now;
            setLevel(Math.max(0.12, Math.min(1, frame.rms * 5)));
          }
          const speaking = phaseRef.current === "speaking" && now - speakStarted.current > 420;
          if (speaking && frame.rms > 0.11) {
            hot.current += 1;
            if (hot.current >= 4) barge();
          } else if (frame.rms < 0.06) {
            hot.current = 0;
          }
        };
        source.connect(worklet);
      } catch {
        setMicNote("Microphone is off. Tap a phrase, or type, and the line still answers.");
      }
    },
    [armThinking, barge, finishSpeak, go, speakOnDevice, stopAudio],
  );

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      wsRef.current?.close();
      void ctxRef.current?.close();
    };
  }, []);

  const setLiveLanguage = useCallback((next: string) => {
    languageRef.current = next;
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "set_language", language: next }));
    }
  }, []);

  const copyShare = useCallback(async () => {
    if (!callState?.share_text) return;
    await navigator.clipboard.writeText(callState.share_text);
    setCopied(true);
  }, [callState]);

  return {
    phase,
    captions,
    callState,
    health,
    error,
    micNote,
    copied,
    level,
    demo,
    apiBase: apiBase(),
    start,
    hangup,
    barge,
    sendText,
    setLiveLanguage,
    copyShare,
  };
}
