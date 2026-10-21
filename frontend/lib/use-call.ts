"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  HEALTH_ABORT_MS,
  HEALTH_KEEPALIVE_MS,
  HEALTH_RETRY_MS,
  deviceSpeechTimeout,
  recognitionLang,
} from "./browser-speech";
import { apiBase, wsBase } from "./endpoints";
import { classifyMic, wakePercent, type LineState } from "./line-status";
import { BROWSER_LANG } from "./phrases";

export type Phase = "idle" | "connecting" | "listening" | "thinking" | "speaking" | "ended" | "error";
export type MicAccess = "unknown" | "live" | "denied" | "missing" | "skipped";

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

function audioContext(): AudioContext {
  const webkit = window as Window & { webkitAudioContext?: typeof AudioContext };
  const Ctx = window.AudioContext || webkit.webkitAudioContext;
  return new Ctx();
}

function requestMic(): Promise<MediaStream> {
  const devices = navigator.mediaDevices;
  if (!devices?.getUserMedia) {
    return Promise.reject(Object.assign(new Error("This browser has no microphone."), { name: "NotSupportedError" }));
  }
  return devices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
}

let voiceList: SpeechSynthesisVoice[] = [];

function rememberVoices() {
  voiceList = window.speechSynthesis?.getVoices?.() ?? voiceList;
}

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  const voices = voiceList.length ? voiceList : (window.speechSynthesis?.getVoices?.() ?? []);
  const prefix = (lang || "hi-IN").slice(0, 2).toLowerCase();
  const same = voices.filter((voice) => voice.lang.toLowerCase().startsWith(prefix));
  return same.find((voice) => /female|woman|natural/i.test(voice.name)) || same[0] || null;
}

type BrowserRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: BrowserSpeechEvent) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type BrowserSpeechEvent = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

function recognitionCtor(): (new () => BrowserRecognition) | null {
  const host = window as Window & {
    SpeechRecognition?: new () => BrowserRecognition;
    webkitSpeechRecognition?: new () => BrowserRecognition;
  };
  return host.SpeechRecognition || host.webkitSpeechRecognition || null;
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
  const [line, setLine] = useState<LineState>("waking");
  const [wakeProgress, setWakeProgress] = useState(8);
  const [mic, setMic] = useState<MicAccess>("unknown");
  const [speechBlock, setSpeechBlock] = useState<string | null>(null);
  const [browserEar, setBrowserEar] = useState(false);

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
  const workletReady = useRef(false);
  const queued = useRef<string[]>([]);
  const callGen = useRef(0);
  const languageRef = useRef(language);
  const healthRef = useRef<Health | null>(null);
  const recRef = useRef<BrowserRecognition | null>(null);
  const sendTextRef = useRef<(text: string, nextLanguage?: string) => void>(() => undefined);
  const armEarRef = useRef<() => void>(() => undefined);
  languageRef.current = language;

  const go = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);

  useEffect(() => {
    const synth = window.speechSynthesis;
    if (!synth) return;
    const load = () => {
      rememberVoices();
    };
    load();
    synth.addEventListener("voiceschanged", load);
    return () => synth.removeEventListener("voiceschanged", load);
  }, []);

  useEffect(() => {
    let gone = false;
    const started = Date.now();
    let awake = false;
    const tick = window.setInterval(() => {
      if (gone || awake) return;
      setWakeProgress(wakePercent(Date.now() - started));
    }, 400);

    async function ping(): Promise<Health | null> {
      const controller = new AbortController();
      const timer = window.setTimeout(() => controller.abort(), HEALTH_ABORT_MS);
      try {
        const response = await fetch(`${apiBase()}/api/health`, { cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("down");
        return (await response.json()) as Health;
      } catch {
        return null;
      } finally {
        window.clearTimeout(timer);
      }
    }

    function apply(body: Health) {
      awake = true;
      healthRef.current = body;
      setHealth(body);
      setLine("ready");
      setWakeProgress(100);
    }

    async function untilAwake(mark: number) {
      while (!gone && !awake) {
        const body = await ping();
        if (gone) return;
        if (body) {
          apply(body);
          return;
        }
        if (Date.now() - mark > HEALTH_ABORT_MS * 2) setLine("down");
        await new Promise((resolve) => window.setTimeout(resolve, HEALTH_RETRY_MS));
      }
    }

    async function wake() {
      await untilAwake(started);
      while (!gone) {
        await new Promise((resolve) => window.setTimeout(resolve, HEALTH_KEEPALIVE_MS));
        if (gone) return;
        const body = (await ping()) || (await ping());
        if (gone) return;
        if (body) {
          apply(body);
          continue;
        }
        awake = false;
        setLine("waking");
        setWakeProgress(8);
        await untilAwake(Date.now());
      }
    }

    void wake();
    return () => {
      gone = true;
      window.clearInterval(tick);
    };
  }, []);

  useEffect(() => {
    if (line !== "ready" || health?.speech !== "mock") {
      setSpeechBlock(null);
      return;
    }
    let gone = false;
    async function probe() {
      const notes: string[] = [];
      try {
        const form = new FormData();
        form.append("language", "hi");
        form.append("file", new Blob([new Uint8Array(16)], { type: "audio/wav" }), "clip.wav");
        const stt = await fetch(`${apiBase()}/api/stt`, { method: "POST", body: form });
        if (stt.status === 409) {
          const body = (await stt.json().catch(() => ({}))) as { detail?: string };
          if (body.detail) notes.push(body.detail);
        }
      } catch {
        /* The banner still explains mock mode if this probe cannot run. */
      }
      try {
        const tts = await fetch(`${apiBase()}/api/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: " ", language: "hi" }),
        });
        if (tts.status === 409) {
          const body = (await tts.json().catch(() => ({}))) as { detail?: string };
          if (body.detail && !notes.includes(body.detail)) notes.push(body.detail);
        }
      } catch {
        /* Same as the speech-to-text probe. */
      }
      if (!gone) setSpeechBlock(notes.length ? notes.join(" ") : null);
    }
    void probe();
    return () => {
      gone = true;
    };
  }, [health?.speech, line]);

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
      // Do not cancel() here. Chrome drops the new utterance when cancel runs in the same turn.
      window.speechSynthesis.speak(utterance);
      window.setTimeout(done, deviceSpeechTimeout(clean));
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

  const stopEar = useCallback(() => {
    const rec = recRef.current;
    recRef.current = null;
    setBrowserEar(false);
    if (!rec) return;
    try {
      rec.onend = null;
      rec.stop();
    } catch {
      /* already stopped */
    }
  }, []);

  const armEar = useCallback(() => {
    const Ctor = recognitionCtor();
    if (!Ctor) {
      setMicNote("This browser cannot hear speech. Type a line, or tap a phrase. JanVaani still answers.");
      setMic("missing");
      return;
    }
    stopEar();
    const rec = new Ctor();
    rec.lang = recognitionLang(languageRef.current);
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (event) => {
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (!result?.isFinal) continue;
        const text = result[0]?.transcript?.trim();
        if (text) sendTextRef.current(text);
      }
    };
    rec.onerror = (event) => {
      const name = event.error || "";
      if (name === "not-allowed" || name === "service-not-allowed") setMic("denied");
      if (name === "audio-capture") {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
    rec.onend = () => {
      window.setTimeout(() => {
        if (recRef.current !== rec) return;
        const phaseNow = phaseRef.current;
        const live = phaseNow === "listening" || phaseNow === "thinking" || phaseNow === "speaking" || phaseNow === "connecting";
        if (!live) return;
        rec.lang = recognitionLang(languageRef.current);
        try {
          rec.start();
        } catch {
          /* Chrome throws if start overlaps the previous session. onend will try again. */
        }
      }, 350);
    };
    recRef.current = rec;
    setBrowserEar(true);
    try {
      rec.start();
    } catch {
      setMicNote("The browser did not start listening. Tap Try the microphone again, or type a line.");
    }
  }, [stopEar]);
  armEarRef.current = armEar;

  const hangup = useCallback(() => {
    stopEar();
    stopAudio();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
    setLevel(0.15);
    go("ended");
  }, [go, stopAudio, stopEar]);

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
      const trimmed = text.trim();
      if (!trimmed) return;
      const socket = wsRef.current;
      if (nextLanguage && nextLanguage !== "auto") {
        languageRef.current = nextLanguage;
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "set_language", language: nextLanguage }));
        }
      }
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        if (phaseRef.current === "connecting") queued.current.push(trimmed);
        return;
      }
      armThinking();
      socket.send(JSON.stringify({ type: "utterance", text: trimmed }));
    },
    [armThinking],
  );
  sendTextRef.current = sendText;

  const attachStream = useCallback(
    async (ctx: AudioContext, media: MediaStream, ticket: number) => {
      if (callGen.current !== ticket) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = media;
      if (ctx.state === "closed") return;
      if (!workletReady.current) {
        await ctx.audioWorklet.addModule("/pcm-worklet.js");
        workletReady.current = true;
      }
      const closed = (ctx.state as AudioContextState) === "closed";
      if (callGen.current !== ticket || closed) {
        media.getTracks().forEach((track) => track.stop());
        if (streamRef.current === media) streamRef.current = null;
        return;
      }
      const source = ctx.createMediaStreamSource(media);
      const worklet = new AudioWorkletNode(ctx, "pcm-downsample");
      worklet.port.onmessage = (event) => {
        const frame = event.data;
        if (!frame || frame.type !== "frame") return;
        const socket = wsRef.current;
        if (socket && socket.readyState === WebSocket.OPEN) socket.send(frame.pcm.buffer);
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
    },
    [barge],
  );

  const enableMic = useCallback(async () => {
    const ticket = ++callGen.current;
    const current = ctxRef.current;
    const ctx = current && current.state !== "closed" ? current : audioContext();
    if (ctx !== current) {
      ctxRef.current = ctx;
      workletReady.current = false;
      playerRef.current = makePlayer(ctx);
    }
    // Both calls stay inside the tap, before the first await.
    const resumePromise = ctx.resume();
    const micPromise = requestMic();
    if (healthRef.current?.speech === "mock") {
      void resumePromise.catch(() => undefined);
      armEarRef.current();
      try {
        const media = await micPromise;
        media.getTracks().forEach((track) => track.stop());
        if (callGen.current !== ticket) return;
        setMic("live");
        setMicNote(null);
      } catch (err) {
        if (callGen.current !== ticket) return;
        setMic(classifyMic(err));
      }
      return;
    }
    void resumePromise.catch(() => undefined);
    try {
      const media = await micPromise;
      if (callGen.current !== ticket) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      await attachStream(ctx, media, ticket);
      if (callGen.current !== ticket) return;
      setMic("live");
      setMicNote(null);
    } catch (err) {
      if (callGen.current !== ticket) return;
      setMic(classifyMic(err));
    }
  }, [attachStream]);

  const start = useCallback(
    async (options?: { demo?: boolean }) => {
      const asDemo = Boolean(options?.demo);
      const ticket = ++callGen.current;
      // Stop the previous call first, still inside the tap, so the unlock
      // utterance below is not cancelled.
      stopEar();
      stopAudio();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      wsRef.current?.close();

      // Keep this block free of await. Mobile browsers only treat getUserMedia
      // and AudioContext.resume as a user gesture when they start in the tap.
      const previous = ctxRef.current;
      const ctx = audioContext();
      ctxRef.current = ctx;
      workletReady.current = false;
      const browserEarNow = !asDemo && healthRef.current?.speech === "mock";
      const resumePromise = ctx.resume();
      playerRef.current = makePlayer(ctx);
      const micPromise = asDemo ? null : requestMic();
      try {
        const unlock = new SpeechSynthesisUtterance(" ");
        unlock.volume = 0;
        window.speechSynthesis?.speak(unlock);
      } catch {
        /* The device voice is optional. The call still runs. */
      }
      if (previous && previous !== ctx && previous.state !== "closed") void previous.close();

      setError(null);
      setMicNote(null);
      setMic(asDemo ? "skipped" : "unknown");
      setCaptions([]);
      setCopied(false);
      setDemo(asDemo);
      setLevel(0.15);
      go("connecting");
      if (browserEarNow) armEar();

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
          if (message.listen === "browser" && !message.demo) {
            if (!recRef.current) armEar();
          } else if (!message.demo) {
            stopEar();
          }
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
        setError("The call could not connect. The line may still be waking up. Tap Start talking again.");
        go("error");
        if (micPromise) {
          void micPromise.then((media) => media.getTracks().forEach((track) => track.stop())).catch(() => undefined);
        }
        return;
      }

      void resumePromise.catch(() => undefined);
      if (socket.readyState !== WebSocket.OPEN) {
        go("error");
        return;
      }
      const chosen = languageRef.current;
      if (asDemo) {
        queued.current = [];
        socket.send(JSON.stringify({ type: "demo", language: chosen === "auto" ? "hi" : chosen }));
        setMicNote("Demo mode uses a practice household, so the microphone stays off. You can still type a line.");
        return;
      }
      socket.send(JSON.stringify({ type: "start", language: chosen }));
      const pending = queued.current.splice(0);
      for (const text of pending) socket.send(JSON.stringify({ type: "utterance", text }));

      if (browserEarNow) {
        if (micPromise) {
          void micPromise
            .then((media) => {
              media.getTracks().forEach((track) => track.stop());
              if (callGen.current !== ticket) return;
              setMic("live");
            })
            .catch((err) => {
              if (callGen.current !== ticket) return;
              setMic(classifyMic(err));
            });
        }
        return;
      }

      if (!micPromise) return;
      try {
        const media = await micPromise;
        if (wsRef.current !== socket || callGen.current !== ticket) {
          media.getTracks().forEach((track) => track.stop());
          return;
        }
        await attachStream(ctx, media, ticket);
        if (callGen.current !== ticket) return;
        setMic("live");
        setMicNote(null);
      } catch (err) {
        if (callGen.current !== ticket) return;
        setMic(classifyMic(err));
      }
    },
    [armEar, armThinking, attachStream, finishSpeak, go, speakOnDevice, stopAudio, stopEar],
  );

  useEffect(() => {
    return () => {
      const rec = recRef.current;
      recRef.current = null;
      try {
        rec?.stop();
      } catch {
        /* already stopped */
      }
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
    const rec = recRef.current;
    if (rec) {
      rec.lang = recognitionLang(next);
      try {
        rec.stop();
      } catch {
        /* onend starts it again with the new language */
      }
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
    line,
    wakeProgress,
    mic,
    speechBlock,
    browserEar,
    apiBase: apiBase(),
    start,
    enableMic,
    hangup,
    barge,
    sendText,
    setLiveLanguage,
    copyShare,
  };
}
