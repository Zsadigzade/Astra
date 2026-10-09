import test from "node:test";
import assert from "node:assert/strict";
import { LIVE_WINDOW_S, isLive, leadingHistory, nextSpeaker, thinkMs } from "./pacing.js";

const line = (ts, speaker) => ({ ts, data: { speaker, text: "x" } });

test("a line is live only inside the window", () => {
  assert.equal(isLive(100, 100 + LIVE_WINDOW_S - 1), true);
  assert.equal(isLive(100, 100 + LIVE_WINDOW_S + 1), false);
});

test("thinking time grows with the line and shrinks under a backlog, within sane bounds", () => {
  assert.ok(thinkMs("hi", 0) >= 650);
  assert.ok(thinkMs("x".repeat(500), 0) <= 650 + 800);
  assert.ok(thinkMs("x".repeat(60), 0) > thinkMs("hi", 0));
  assert.ok(thinkMs("x".repeat(60), 6) < thinkMs("x".repeat(60), 0));
  assert.ok(Number.isFinite(thinkMs(undefined, 0)));
});

test("viktor opens, then speakers alternate, and nobody thinks when the haggle is over", () => {
  assert.equal(nextSpeaker([], true), "viktor");
  assert.equal(nextSpeaker([line(1, "viktor")], true), "max");
  assert.equal(nextSpeaker([line(1, "viktor"), line(2, "max")], true), "viktor");
  assert.equal(nextSpeaker([line(1, "viktor")], false), null);
});

test("opening a deal shows old lines at once and keeps only the fresh tail for pacing", () => {
  const chat = [line(1, "viktor"), line(2, "max"), line(995, "viktor")];
  assert.equal(leadingHistory(chat, 1000), 2);
  assert.equal(leadingHistory(chat, 5000), 3);
  assert.equal(leadingHistory([], 1000), 0);
});
