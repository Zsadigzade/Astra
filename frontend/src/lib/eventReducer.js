// Pure view-model derivation from the buyer SSE history. No React, no network: unit-testable.
// Everything shown on the dashboard comes from here; nothing is invented that the backend did not send.
import { describeEvent, provenanceOf } from "./eventLabels.js";
import { tada } from "./formatters.js";

export const STAGES = [
  ["negotiate", "Negotiate", "Max and Viktor agree a price"],
  ["guard", "Guard", "The wallet guard checks the price against cap, budget and approval line"],
  ["escrow", "Escrow", "Funds are locked in escrow before any work starts"],
  ["delivery", "Delivery", "Viktor delivers the data"],
  ["verify", "Verify", "Rule-based checks on the delivery"],
  ["settle", "Settle", "Release to Viktor, or refund to Max"],
];

const TERMINAL = ["released", "refunded", "blocked", "walked_away", "error"];

const byDeal = (events, dealId) => events.filter((e) => e.deal_id === dealId);
const last = (events, ...types) => [...events].reverse().find((e) => types.includes(e.type));
const has = (events, ...types) => events.some((e) => types.includes(e.type));

export function outcomeOf(deal) {
  if (has(deal, "released")) return "released";
  if (has(deal, "refunded")) return "refunded";
  if (has(deal, "blocked")) return "blocked";
  if (has(deal, "walked_away")) return "walked";
  if (has(deal, "error")) return "error";
  return "running";
}

// status per pipeline stage: idle | active | done | fail | wait
export function stagesOf(deal) {
  const outcome = outcomeOf(deal);
  const s = Object.fromEntries(STAGES.map(([k]) => [k, "idle"]));
  if (!deal.length) return s;
  s.negotiate = has(deal, "quote") ? "done" : outcome === "walked" ? "fail" : "active";
  if (has(deal, "quote") || has(deal, "blocked")) {
    const paid = has(deal, "escrow_locked", "already_paid");
    const waiting = has(deal, "needs_approval") && !has(deal, "approved", "blocked") && !paid;
    s.guard = has(deal, "blocked") && !paid ? "fail" : waiting ? "wait" : paid || has(deal, "approved") ? "done" : "active";
  }
  if (has(deal, "escrow_locked", "already_paid")) s.escrow = "done";
  else if (s.guard === "done") s.escrow = "active";
  if (has(deal, "delivered")) s.delivery = "done";
  else if (s.escrow === "done") s.delivery = "active";
  const verified = last(deal, "verified");
  if (verified) s.verify = verified.data.ok ? "done" : "fail";
  else if (s.delivery === "done") s.verify = "active";
  if (outcome === "released") s.settle = last(deal, "released")?.data.release === "scheduled" ? "wait" : "done";
  else if (outcome === "refunded") s.settle = "fail";
  else if (verified) s.settle = "active";
  if (outcome === "error") {
    const cur = STAGES.map(([k]) => k).find((k) => s[k] === "active");
    if (cur) s[cur] = "fail";
  }
  return s;
}

export function pendingApprovals(events) {
  return events.filter(
    (e) => e.type === "needs_approval" &&
      !events.some((x) => x.deal_id === e.deal_id && ["approved", "blocked"].includes(x.type) && x.id > e.id),
  );
}

// The wallet guard's plain-language state for the current deal.
// status: ready | checking | safe | approval | blocked | escrow | verify_failed | release_scheduled | released | refunded | no_payment
export function guardOf(deal, stages, outcome) {
  if (!deal.length) return { status: "ready", tone: "neutral", title: "Ready", message: "Every price is checked before any payment." };
  const blocked = last(deal, "blocked");
  const paid = has(deal, "escrow_locked", "already_paid");
  if (blocked && !paid) return { status: "blocked", tone: "danger", title: "Payment blocked", message: `Blocked before payment: ${blocked.data.reason}.` };
  const rel = last(deal, "released");
  if (rel) {
    return rel.data.release === "scheduled"
      ? { status: "release_scheduled", tone: "success", title: "Release scheduled", message: `Release of ${tada(rel.data.price)} is scheduled${rel.data.settles_at ? ` for ${rel.data.settles_at}` : ""}. It has not settled yet.` }
      : { status: "released", tone: "success", title: "Payment released", message: `${tada(rel.data.price)} released to Viktor after the delivery passed verification.` };
  }
  const ref = last(deal, "refunded");
  if (ref) return { status: "refunded", tone: "warning", title: "Refunded", message: `${tada(ref.data.price)} returned to Max because the delivery failed verification.` };
  const ver = last(deal, "verified");
  if (ver && !ver.data.ok) return { status: "verify_failed", tone: "danger", title: "Verification failed", message: "The delivery did not pass the checks. Escrow is being refunded." };
  const ask = pendingApprovals(deal)[0];
  if (ask) return { status: "approval", tone: "warning", title: "Human approval required", message: `${ask.data.reason}. Payment proceeds only if you approve.` };
  if (paid) return { status: "escrow", tone: "success", title: "Escrow locked", message: "Held until the delivery is verified." };
  if (stages.guard === "done") return { status: "safe", tone: "success", title: "Safe to pay", message: "Within cap, budget and approval line." };
  if (stages.guard === "active") return { status: "checking", tone: "info", title: "Checking", message: "Checking the agreed price." };
  if (outcome === "walked") return { status: "no_payment", tone: "neutral", title: "No payment made", message: last(deal, "walked_away")?.data.reason ?? "The negotiation ended without a deal." };
  if (outcome === "error") return { status: "no_payment", tone: "danger", title: "No payment made", message: last(deal, "error")?.data.message ?? "The deal failed." };
  return { status: "ready", tone: "neutral", title: "Ready", message: "Waiting for an agreed price." };
}

export function terminalOf(outcome, guard) {
  if (guard.status === "release_scheduled") return { tone: "neutral", title: "Release scheduled", description: guard.message };
  const map = {
    released: ["success", "Deal complete", guard.message],
    refunded: ["warning", "Deal refunded", guard.message],
    blocked: ["danger", "Payment blocked", guard.message],
    walked: ["neutral", "Negotiation ended", guard.message],
    error: ["danger", "Deal failed", guard.message],
  };
  const m = map[outcome];
  return m ? { tone: m[0], title: m[1], description: m[2] } : null;
}

export function usageOf(events) {
  const dealIds = [...new Set(events.filter((e) => e.deal_id).map((e) => e.deal_id))];
  const outcomes = { released: 0, refunded: 0, blocked: 0, walked: 0, error: 0, running: 0 };
  let released = 0, refunded = 0, locked = 0, scheduled = 0;
  for (const id of dealIds) {
    const d = byDeal(events, id);
    const o = outcomeOf(d);
    outcomes[o] += 1;
    const lock = last(d, "escrow_locked", "already_paid");
    const price = lock?.data.price ?? 0;
    if (o === "released" && last(d, "released")?.data.release === "scheduled") {
      scheduled += price;
      locked += price;
    } else if (o === "released") released += price;
    else if (o === "refunded") refunded += price;
    else if (lock) locked += price;
  }
  const lines = events.filter((e) => e.type === "negotiation");
  const provenance = lines.map(provenanceOf);
  return {
    deals: dealIds.length,
    outcomes,
    released, refunded, locked, scheduled,
    lines: lines.length,
    viktor: lines.filter((e) => e.data.speaker === "viktor").length,
    codex: provenance.filter((p) => p === "codex").length,
    scripted: provenance.filter((p) => p === "scripted" || p === "fallback").length,
    fallback: provenance.filter((p) => p === "fallback").length,
    voice: lines.filter((e) => e.data.audio_url).length,
  };
}

// Readable timeline across all deals, newest first. Only the first negotiation line of a deal is listed.
export function timelineOf(events) {
  const seenNegotiation = new Set();
  const rows = [];
  for (const e of events) {
    if (e.type === "negotiation") {
      if (seenNegotiation.has(e.deal_id)) continue;
      seenNegotiation.add(e.deal_id);
    }
    const d = describeEvent(e);
    if (d) rows.push({ id: e.id, ts: e.ts, staged: e.staged, ...d, event: e });
  }
  return rows.reverse();
}

// One row per deal, newest first: what the Deals tab lists.
export function dealsOf(events) {
  const ids = [...new Set(events.filter((e) => e.deal_id).map((e) => e.deal_id))];
  return ids.map((id) => {
    const d = byDeal(events, id);
    const created = d.find((e) => e.type === "task_created");
    const delivered = last(d, "delivered");
    return {
      dealId: id, ts: created?.ts ?? d[0].ts, text: created?.data.text ?? null, scenario: created?.data.demo_mode ?? null,
      staged: d.some((e) => e.staged), outcome: outcomeOf(d), price: last(d, "quote")?.data.price ?? null,
      items: delivered?.data.items ?? null, source: delivered?.data.source ?? null,
    };
  }).reverse();
}

// dealId picks a past deal to look at; without it (or if unknown) the latest deal is shown.
export function deriveDealState(events, dealId = null) {
  const latestId = [...events].reverse().find((e) => e.deal_id)?.deal_id ?? null;
  const current = dealId && events.some((e) => e.deal_id === dealId) ? dealId : latestId;
  const deal = current ? byDeal(events, current) : [];
  const created = deal.find((e) => e.type === "task_created");
  const chat = deal.filter((e) => e.type === "negotiation").map((e) => ({ ...e, provenance: provenanceOf(e) }));
  const lastPrice = (who) => [...chat].reverse().find((e) => e.data.speaker === who && e.data.price > 0)?.data.price ?? null;
  const outcome = outcomeOf(deal);
  const stages = stagesOf(deal);
  const guard = guardOf(deal, stages, outcome);
  const lock = last(deal, "escrow_locked", "already_paid");
  const delivered = last(deal, "delivered");
  const pending = pendingApprovals(events);
  const latest = chat[chat.length - 1];
  return {
    dealId: current,
    scenario: created?.data.demo_mode ?? null,
    outcome,
    stages,
    guard,
    terminal: terminalOf(outcome, guard),
    task: created?.data ?? null,
    staged: deal.some((e) => e.staged),
    simulated: events.length ? events[events.length - 1].simulated : null,
    chat,
    round: chat.filter((e) => e.data.speaker === "viktor").length,
    prices: { max: lastPrice("max"), viktor: lastPrice("viktor"), current: latest?.data.price > 0 ? latest.data.price : null },
    agreed: last(deal, "quote")?.data.price ?? null,
    balances: last(events, "balances")?.data ?? null,
    pending,
    approval: pending.find((e) => e.deal_id === current) ?? pending[0] ?? null,
    escrow: lock ? { ...lock.data, resumed: lock.type === "already_paid" } : null,
    release: last(deal, "released")?.data ?? null,
    refund: last(deal, "refunded")?.data ?? null,
    delivery: delivered ? { items: delivered.data.items, source: delivered.data.source, result: delivered.data.result } : null,
    verified: last(deal, "verified")?.data ?? null,
    finished: has(deal, ...TERMINAL),
    usage: usageOf(events),
    timeline: timelineOf(events),
    deals: dealsOf(events),
    isLatest: current === latestId,
  };
}
