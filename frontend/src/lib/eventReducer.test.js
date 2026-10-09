import test from "node:test";
import assert from "node:assert/strict";
import { appendEvent } from "../eventIdentity.js";
import { PROVENANCE } from "./eventLabels.js";
import { dealsOf, deriveDealState, stagesOf, usageOf, pendingApprovals, guardOf, timelineOf } from "./eventReducer.js";

let n = 0;
const ev = (type, data = {}, o = {}) => ({ id: ++n, ts: n, deal_id: "d1", task_id: "t1", simulated: true, staged: false, type, data, ...o });

const honest = () => [
  ev("task_created", { budget: 20, demo_mode: "honest" }),
  ev("negotiation", { speaker: "viktor", price: 18, text: "18", backend: "mock" }),
  ev("negotiation", { speaker: "max", price: 5, text: "5", backend: "mock" }),
  ev("quote", { price: 7 }),
  ev("escrow_locked", { price: 7, ref: "r" }),
  ev("delivered", { items: 20, source: "sample" }),
  ev("verified", { ok: true }),
  ev("released", { price: 7 }),
];

test("delayed speech hydrates its original line without selecting an older deal", () => {
  const line = ev("negotiation", { audio_status: "pending", text: "Hello" });
  const created = ev("task_created", {}, { deal_id: "new" });
  const completion = ev("audio_ready", { message_id: line.id, message_ts: line.ts,
    audio_status: "ready", audio_url: "/audio/hello.mp3" });
  const view = deriveDealState([line, created, completion]);
  assert.equal(view.dealId, "new");
  assert.equal(view.usage.voice, 1);
  assert.equal(deriveDealState([line, completion]).chat[0].data.audio_url, "/audio/hello.mp3");
});

test("stale cached delivery facts survive derivation without changing provenance", () => {
  const view = deriveDealState([ev("delivered", { items: 20, source: "apify_cached",
    result: { cache_stale: true, cache_age_seconds: 172800, fetched_at: "2026-10-07T00:00:00Z" } })]);
  assert.equal(view.delivery.source, "apify_cached");
  assert.equal(view.delivery.result.cache_stale, true);
  assert.equal(view.delivery.result.cache_age_seconds, 172800);
});

test("honest deal runs every stage to done and counts released spend", () => {
  const v = deriveDealState(honest());
  assert.equal(v.outcome, "released");
  assert.deepEqual(Object.values(v.stages), ["done", "done", "done", "done", "done", "done"]);
  assert.equal(v.agreed, 7);
  assert.equal(v.scenario, "honest");
  assert.deepEqual([v.prices.max, v.prices.viktor], [5, 18]);
  assert.equal(v.round, 1);
  assert.equal(v.usage.released, 7);
  assert.equal(v.terminal.title, "Deal complete");
});

test("blocked deal fails the guard stage, never reaches escrow, and says why", () => {
  const v = deriveDealState([ev("task_created", { demo_mode: "con" }), ev("quote", { price: 250 }), ev("blocked", { reason: "$250 is over the hard cap of $100" }), ev("walked_away")]);
  assert.equal(v.outcome, "blocked");
  assert.equal(v.stages.guard, "fail");
  assert.equal(v.stages.escrow, "idle");
  assert.equal(v.guard.status, "blocked");
  assert.match(v.guard.message, /over the hard cap of \$100/);
});

test("junk delivery fails verify and settles as a refund", () => {
  const deal = [ev("quote", { price: 7 }), ev("escrow_locked", { price: 7 }), ev("delivered", {}), ev("verified", { ok: false }), ev("refunded", { price: 7 })];
  const s = stagesOf(deal);
  assert.equal(s.verify, "fail");
  assert.equal(s.settle, "fail");
  assert.equal(guardOf(deal, s, "refunded").status, "refunded");
  assert.equal(guardOf(deal.slice(0, 4), stagesOf(deal.slice(0, 4)), "running").status, "verify_failed");
});

test("approval stays pending until approved or blocked and drives the guard state", () => {
  const ask = ev("needs_approval", { price: 90, reason: "$90 is over the approval line of $80" });
  assert.equal(pendingApprovals([ask]).length, 1);
  assert.equal(pendingApprovals([ask, ev("approved")]).length, 0);
  const v = deriveDealState([ev("task_created", {}), ev("quote", { price: 90 }), ask]);
  assert.equal(v.stages.guard, "wait");
  assert.equal(v.guard.status, "approval");
  assert.equal(v.approval.data.price, 90);
});

test("guard walks ready -> checking -> safe -> escrow as the deal progresses", () => {
  const status = (events) => deriveDealState(events).guard.status;
  assert.equal(status([]), "ready");
  assert.equal(status([ev("task_created", {})]), "ready");
  assert.equal(status([ev("task_created", {}), ev("quote", { price: 7 })]), "checking");
  assert.equal(status([ev("task_created", {}), ev("quote", { price: 90 }), ev("needs_approval", { price: 9, reason: "r" }), ev("approved", {})]), "safe");
  assert.equal(status([ev("quote", { price: 7 }), ev("escrow_locked", { price: 7 })]), "escrow");
});

test("a scheduled Masumi release is reported as scheduled, not settled", () => {
  const v = deriveDealState([ev("quote", { price: 7 }), ev("escrow_locked", { price: 7 }), ev("delivered", {}), ev("verified", { ok: true }),
    ev("released", { price: 7, release: "scheduled", settles_at: "2026-10-09T05:00Z" })]);
  assert.equal(v.guard.status, "release_scheduled");
  assert.match(v.guard.message, /not settled|has not settled/);
  assert.equal(v.usage.released, 0);
  assert.equal(v.usage.locked, 7);
  assert.equal(v.usage.scheduled, 7);
  assert.equal(v.stages.settle, "wait");
  assert.equal(v.terminal.title, "Release scheduled");
});

test("failed funded deals keep escrow counted until release or refund", () => {
  const events = [ev("escrow_locked", { price: 7 }), ev("error", { message: "Seller unreachable" })];
  const failed = usageOf(events);
  assert.equal(failed.locked, 7);
  assert.equal(failed.released, 0);
  assert.equal(failed.refunded, 0);
  const recovered = usageOf([...events, ev("already_paid", { price: 7 }), ev("released", { price: 7 })]);
  assert.equal(recovered.locked, 0);
  assert.equal(recovered.released, 7);
});

test("negotiation provenance separates subscription Codex, scripted and fallback lines", () => {
  const v = deriveDealState([
    ev("negotiation", { speaker: "max", backend: "codex" }),
    ev("negotiation", { speaker: "max", backend: "mock", fallback_reason: "Timeout" }),
    ev("negotiation", { speaker: "max", backend: "mock" }),
    ev("negotiation", { speaker: "max", backend: "guard" }),
  ]);
  assert.deepEqual(v.chat.map((c) => c.provenance), ["codex", "fallback", "scripted", "guard"]);
});

test("usage counts subscription Codex, scripted, fallback and voice lines", () => {
  const u = usageOf([
    ev("negotiation", { speaker: "max", backend: "codex" }),
    ev("negotiation", { speaker: "max", backend: "mock", fallback_reason: "Timeout" }),
    ev("negotiation", { speaker: "max", backend: "mock", audio_url: "/audio/a.mp3" }),
    ev("negotiation", { speaker: "viktor", backend: "mock" }),
  ]);
  assert.deepEqual([u.codex, u.scripted, u.fallback, u.voice, u.lines], [1, 3, 1, 1, 4]);
});

test("seller subscription, fallback and legacy scripted lines retain truthful provenance", () => {
  const v = deriveDealState([
    ev("negotiation", { speaker: "viktor", backend: "codex" }),
    ev("negotiation", { speaker: "viktor", backend: "mock", fallback_reason: "Timeout" }),
    ev("negotiation", { speaker: "viktor", backend: "mock" }, { staged: true }),
    ev("negotiation", { speaker: "viktor" }),
    ev("negotiation", { speaker: "max", backend: "codex" }),
    ev("negotiation", { speaker: "max", backend: "guard" }),
  ]);
  assert.deepEqual(v.chat.map((c) => c.provenance), ["codex", "fallback", "scripted", "scripted", "codex", "guard"]);
  assert.equal(PROVENANCE[v.chat[0].provenance].label, "CODEX SUBSCRIPTION");
  assert.equal(PROVENANCE[v.chat[1].provenance].label, "SCRIPTED FALLBACK");
  assert.deepEqual([v.usage.codex, v.usage.scripted, v.usage.fallback, v.usage.viktor, v.usage.lines], [2, 3, 1, 4, 6]);
});

test("timeline is newest-first, readable, and collapses the haggle to one entry", () => {
  const rows = timelineOf(honest());
  assert.equal(rows[0].title, "Payment released");
  assert.equal(rows.filter((r) => r.title === "Negotiation started").length, 1);
  assert.ok(rows.every((r) => r.event && r.title && r.description));
  assert.ok(!rows.some((r) => /balances/i.test(r.title)));
});

test("empty stream is a safe idle view", () => {
  const v = deriveDealState([]);
  assert.equal(v.dealId, null);
  assert.equal(v.outcome, "running");
  assert.equal(v.simulated, null);
  assert.equal(v.guard.status, "ready");
  assert.equal(v.terminal, null);
});


test("reset with reused event IDs selects the new deal and preserves Codex provenance", () => {
  const before = ev("negotiation", { speaker: "max", backend: "mock", text: "Old" }, { id: 1, ts: 10, deal_id: "old" });
  const after = ev("negotiation", { speaker: "max", backend: "codex", text: "New" }, { id: 1, ts: 20, deal_id: "new" });
  let history = appendEvent([before], after);
  history = appendEvent(history, { ...after });
  const view = deriveDealState(history);
  assert.equal(view.dealId, "new");
  assert.equal(view.chat.length, 1);
  assert.equal(view.chat[0].data.text, "New");
  assert.equal(PROVENANCE[view.chat[0].provenance].label, "CODEX SUBSCRIPTION");
  assert.equal(view.usage.codex, 1);
  assert.equal(view.usage.scripted, 1);
  assert.equal(view.timeline.length, 2);
});


const second = (type, data = {}) => ev(type, data, { deal_id: "d2", task_id: "t2" });

test("deals are listed newest first with outcome, price and delivery", () => {
  const events = [...honest(), second("task_created", { text: "4 flats in Praha 2", demo_mode: "con" }), second("quote", { price: 25 }), second("blocked", { reason: "cap" })];
  const rows = dealsOf(events);
  assert.deepEqual(rows.map((r) => r.dealId), ["d2", "d1"]);
  assert.deepEqual([rows[0].outcome, rows[0].scenario, rows[0].price, rows[0].text], ["blocked", "con", 25, "4 flats in Praha 2"]);
  assert.deepEqual([rows[1].outcome, rows[1].price, rows[1].items, rows[1].source], ["released", 7, 20, "sample"]);
});

test("a past deal can be selected, unknown ids fall back to the latest, isLatest says which", () => {
  const events = [...honest(), second("task_created", { demo_mode: "junk" }), second("quote", { price: 7 })];
  assert.equal(deriveDealState(events).dealId, "d2");
  assert.equal(deriveDealState(events).isLatest, true);
  const past = deriveDealState(events, "d1");
  assert.deepEqual([past.dealId, past.outcome, past.isLatest], ["d1", "released", false]);
  assert.equal(deriveDealState(events, "nope").dealId, "d2");
  assert.deepEqual(dealsOf([]), []);
});

test("the delivery carries when it arrived, so the board only animates fresh results", () => {
  const events = [ev("task_created", {}), ev("delivered", { items: 2, source: "sample", result: { flats: [] } })];
  const v = deriveDealState(events);
  assert.equal(v.delivery.ts, events[1].ts);
  assert.equal(deriveDealState([ev("task_created", {})]).delivery, null);
});
