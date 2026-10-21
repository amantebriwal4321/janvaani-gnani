import assert from "node:assert/strict";
import { HEALTH_ABORT_MS, HEALTH_KEEPALIVE_MS, deviceSpeechTimeout, recognitionLang } from "../frontend/lib/browser-speech.ts";
import { classifyMic, connectionLabel, wakePercent } from "../frontend/lib/line-status.ts";

assert.equal(wakePercent(0), 8);
assert.equal(wakePercent(28000), 92);
assert.equal(wakePercent(60000), 92);
assert.equal(wakePercent(-10), 8);
assert.ok(wakePercent(14000) > 8 && wakePercent(14000) < 92);

assert.equal(connectionLabel({ phase: "idle", demo: false, line: "waking" }), "Waking up the line…");
assert.equal(connectionLabel({ phase: "connecting", demo: false, line: "waking" }), "Waking up the line…");
assert.equal(connectionLabel({ phase: "connecting", demo: false, line: "ready" }), "Connecting");
assert.equal(connectionLabel({ phase: "listening", demo: false, line: "ready" }), "Live");
assert.equal(connectionLabel({ phase: "thinking", demo: false, line: "ready" }), "Live");
assert.equal(connectionLabel({ phase: "speaking", demo: false, line: "ready" }), "Live");
assert.equal(connectionLabel({ phase: "listening", demo: true, line: "ready" }), "Demo mode");
assert.equal(connectionLabel({ phase: "connecting", demo: true, line: "waking" }), "Demo mode");
assert.equal(connectionLabel({ phase: "idle", demo: false, line: "ready" }), "Ready");
assert.equal(connectionLabel({ phase: "idle", demo: false, line: "down" }), "Line is down");
assert.equal(connectionLabel({ phase: "error", demo: false, line: "ready" }), "Line dropped");

assert.equal(classifyMic({ name: "NotAllowedError" }), "denied");
assert.equal(classifyMic({ name: "SecurityError" }), "denied");
assert.equal(classifyMic(new Error("no")), "denied");
assert.equal(classifyMic({ name: "NotFoundError" }), "missing");
assert.equal(classifyMic({ name: "NotSupportedError" }), "missing");
assert.equal(classifyMic({ name: "NotReadableError" }), "missing");

assert.ok(HEALTH_ABORT_MS >= 40000);
assert.ok(HEALTH_KEEPALIVE_MS >= 60000);
assert.equal(recognitionLang("auto"), "hi-IN");
assert.equal(recognitionLang("hi"), "hi-IN");
assert.equal(recognitionLang("hi-en"), "hi-IN");
assert.equal(recognitionLang("kn"), "kn-IN");
assert.equal(recognitionLang("te"), "te-IN");
assert.equal(deviceSpeechTimeout("hi"), 400 + 2 * 35);
assert.ok(deviceSpeechTimeout("x".repeat(500)) <= 9000);
assert.ok(deviceSpeechTimeout("hello") < 20000);

console.log("desk-status ok");
