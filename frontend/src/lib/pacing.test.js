import test from "node:test";
import assert from "node:assert/strict";
import { GAP_MS, LIVE_WINDOW_S, isLive, leadingHistory, nextSpeaker, speakMs, thinkMs } from "./pacing.js";

const line = (ts, speaker) => ({ ts, data: { speaker, text: "x" } });

test("a line is live only inside the window", () => {
  assert.equal(isLive(100, 100 + LIVE_WINDOW_S - 1), true);
  assert.equal(isLive(100, 100 + LIVE_WINDOW_S + 1), false);
});

test("a line created before the page loaded is history however recent it is", () => {
  assert.equal(isLive(995, 1000, 1000), false); // created 5s ago, but before this page loaded
  assert.equal(isLive(1001, 1002, 1000), true); // created after load
});

test("thinking time grows with the line and shrinks under a backlog, within sane bounds", () => {
  assert.ok(thinkMs("hi", 0) >= 650);
  assert.ok(thinkMs("x".repeat(500), 0) <= 650 + 800);
  assert.ok(thinkMs("x".repeat(60), 0) > thinkMs("hi", 0));
  assert.ok(thinkMs("x".repeat(60), 6) < thinkMs("x".repeat(60), 0));
  assert.ok(Number.isFinite(thinkMs(undefined, 0)));
});

test("the speech bubble stays longer for longer text, within 1.6s to 5.5s", () => {
  assert.equal(speakMs("Hi"), 1600);
  assert.ok(speakMs("x".repeat(40)) > speakMs("x".repeat(20)));
  assert.ok(speakMs("x".repeat(60)) > 3500);
  assert.ok(speakMs("x".repeat(90)) > speakMs("x".repeat(60)));
  assert.equal(speakMs("x".repeat(1000)), 5500);
  assert.ok(Number.isFinite(speakMs(undefined)));
});

test("a backlog does not shorten the reading time, only the thinking beat", () => {
  const long = "x".repeat(60);
  assert.equal(speakMs(long), speakMs(long)); // no backlog parameter at all
  assert.ok(thinkMs(long, 6) < thinkMs(long, 0));
  assert.ok(GAP_MS > 0 && GAP_MS < 1000);
});

test("max opens with his question, then speakers alternate, and nobody thinks when the haggle is over", () => {
  assert.equal(nextSpeaker([], true), "max");
  assert.equal(nextSpeaker([line(1, "max")], true), "viktor");
  assert.equal(nextSpeaker([line(1, "max"), line(2, "viktor")], true), "max");
  assert.equal(nextSpeaker([line(1, "max")], false), null);
});

test("opening a deal shows old lines at once and keeps only the fresh tail for pacing", () => {
  const chat = [line(1, "max"), line(2, "viktor"), line(995, "max")];
  assert.equal(leadingHistory(chat, 1000), 2); // no load time given: the two stale lines are history, the fresh one is live
  assert.equal(leadingHistory(chat, 5000), 3);
  assert.equal(leadingHistory(chat, 1000, 990), 2); // loaded at 990: the first two predate the page
  assert.equal(leadingHistory(chat, 1000, 1000), 3); // everything predates a page loaded at 1000
  assert.equal(leadingHistory([], 1000), 0);
});
