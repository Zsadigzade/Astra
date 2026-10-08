import test from "node:test";
import assert from "node:assert/strict";
import { appendEvent, eventKey } from "./eventIdentity.js";

test("SSE reconnect replays do not duplicate existing events", () => {
  const event = { id: 1, ts: "2026-10-08T20:00:00Z", deal_id: "first" };
  const events = [event];
  assert.equal(appendEvent(events, { ...event }), events);
});

test("reset ledger IDs accept fresh events and produce distinct React keys", () => {
  const original = { id: 1, ts: "2026-10-08T20:00:00Z", deal_id: "first" };
  for (const incoming of [
    { ...original, ts: "2026-10-08T21:00:00Z" },
    { ...original, deal_id: "second" },
  ]) {
    assert.deepEqual(appendEvent([original], incoming), [original, incoming]);
    assert.notEqual(eventKey(original), eventKey(incoming));
  }
});
