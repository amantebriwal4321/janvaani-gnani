import assert from "node:assert/strict";
import { classifyMic, connectionLabel, wakePercent } from "./line-status.ts";

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

console.log("line-status ok");
