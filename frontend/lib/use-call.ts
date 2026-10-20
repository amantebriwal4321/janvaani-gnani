"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BROWSER_LANG } from "./phrases";

export type Phase = "idle" | "connecting" | "listening" | "speaking" | "ended" | "error";

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

export type Caption = { role: "user" | "assistant"; text: string };

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

function apiBase() {
  const configured = process.env.NEXT_PUBLIC_API_BASE;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window === "undefined") return "http://127.0.0.1:8766";
  return `${window.location.protocol}//${window.location.hostname}:8766`;
}

function makePlayer(ctx: AudioContext): Player {
  const nodes: AudioBufferSourceNode[] = [];
  let next = 0;
  return {
    push(pcm: ArrayBuffer) {
      const view = new Int16Array(pcm.slice(0));
      const floats = new Float32Array(view.length);
      for (let i = 0; i < view.length; i++) floats[i] = view[i] / 32768;
      const buffer = ctx.createBuffer(1, Math.max(1, floats.length), 8000);
      buffer.copyToChannel(floats, 0);
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      const now = ctx.currentTime;
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
      for (const source of nodes) {
        try {
          source.stop();
        } catch {
          /* already stopped */
        }
      }
      nodes.length = 0;
      next = 0;
    },
    remaining() {
      return Math.max(0, next - ctx.currentTime);
    },
  };
}

export function useCall(language: string) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [callState, setCallState] = useState<CallState | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [micNote, setMicNote] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<Player | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const phaseRef = useRef<Phase>("idle");
  const speakTurn = useRef<number | null>(null);
  const speakStarted = useRef(0);
  const hot = useRef(0);
  const languageRef = useRef(language);
  languageRef.current = language;
  phaseRef.current = phase;

  useEffect(() => {
    let gone = false;
    fetch(`${apiBase()}/api/health`)
      .then((response) => response.json())
      .then((body) => {
        if (!gone) setHealth(body);
      })
      .catch(() => {
        if (!gone) setError("The JanVaani line is not up. Start the server and try the call again.");
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
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.lang = lang || "hi-IN";
      utterance.rate = 0.95;
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
      window.setTimeout(done, Math.min(22000, 900 + clean.length * 75));
    },
    [finishSpeak],
  );

  const hangup = useCallback(() => {
    stopAudio();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setPhase("ended");
  }, [stopAudio]);

  const barge = useCallback(() => {
    hot.current = 0;
    stopAudio();
    const socket = wsRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "barge_in" }));
    }
    if (phaseRef.current === "speaking") setPhase("listening");
  }, [stopAudio]);

  const sendText = useCallback((text: string, nextLanguage?: string) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (nextLanguage && nextLanguage !== "auto") {
      socket.send(JSON.stringify({ type: "set_language", language: nextLanguage }));
    }
    socket.send(JSON.stringify({ type: "utterance", text }));
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setMicNote(null);
    setCaptions([]);
    setCallState(null);
    setCopied(false);
    setPhase("connecting");
    const socket = new WebSocket(`${apiBase().replace(/^http/, "ws")}/ws/call`);
    socket.binaryType = "arraybuffer";
    wsRef.current = socket;

    socket.onmessage = (event) => {
      if (typeof event.data !== "string") {
        playerRef.current?.push(event.data as ArrayBuffer);
        return;
      }
      const message = JSON.parse(event.data);
      if (message.type === "ready") {
        setPhase("listening");
      } else if (message.type === "status") {
        if (message.phase === "speaking") {
          setPhase("speaking");
          speakStarted.current = Date.now();
          speakTurn.current = message.turnId ?? null;
        } else if (message.phase === "listening") {
          if (message.barged) stopAudio();
          setPhase("listening");
        }
      } else if (message.type === "transcript") {
        setCaptions((current) => [...current, { role: message.role, text: message.text }].slice(-8));
      } else if (message.type === "state") {
        setCallState(message.state);
      } else if (message.type === "clear") {
        stopAudio();
        setPhase("listening");
      } else if (message.type === "speak" && message.audio === "browser") {
        setPhase("speaking");
        speakStarted.current = Date.now();
        speakTurn.current = message.turnId ?? null;
        const lang = message.browserLang || BROWSER_LANG[message.language] || "hi-IN";
        speakOnDevice(message.text || "", lang, message.turnId);
      } else if (message.type === "audio_start") {
        setPhase("speaking");
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

    socket.onerror = () => setError("The call could not connect. Check that the backend is running.");
    socket.onclose = () => {
      if (phaseRef.current !== "ended" && phaseRef.current !== "idle") setPhase("ended");
    };

    await new Promise<void>((resolve, reject) => {
      socket.onopen = () => resolve();
      socket.addEventListener("error", () => reject(new Error("socket")), { once: true });
    }).catch(() => {
      setError("The call could not connect. Check that the backend is running.");
      setPhase("error");
    });

    if (socket.readyState !== WebSocket.OPEN) {
      setPhase("error");
      return;
    }
    socket.send(JSON.stringify({ type: "start", language: languageRef.current }));

    try {
      const media = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      });
      streamRef.current = media;
      const ctx = new AudioContext();
      ctxRef.current = ctx;
      void ctx.resume();
      playerRef.current = makePlayer(ctx);
      await ctx.audioWorklet.addModule("/pcm-worklet.js");
      const source = ctx.createMediaStreamSource(media);
      const worklet = new AudioWorkletNode(ctx, "pcm-downsample");
      worklet.port.onmessage = (event) => {
        const frame = event.data;
        if (!frame || frame.type !== "frame") return;
        if (socket.readyState === WebSocket.OPEN) socket.send(frame.pcm.buffer);
        const speaking = phaseRef.current === "speaking" && Date.now() - speakStarted.current > 700;
        if (speaking && frame.rms > 0.11) {
          hot.current += 1;
          if (hot.current >= 4) barge();
        } else if (frame.rms < 0.06) {
          hot.current = 0;
        }
      };
      source.connect(worklet);
    } catch {
      const ctx = new AudioContext();
      ctxRef.current = ctx;
      void ctx.resume();
      playerRef.current = makePlayer(ctx);
      setMicNote("Microphone is off. Tap a phrase, or type, and the line still answers.");
    }
  }, [barge, finishSpeak, speakOnDevice, stopAudio]);

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
    apiBase: apiBase(),
    start,
    hangup,
    barge,
    sendText,
    setLiveLanguage,
    copyShare,
  };
}
