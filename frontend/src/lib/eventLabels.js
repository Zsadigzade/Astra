// Human-readable titles and descriptions for backend events. Never invents data: every
// description is built from fields the event actually carried.
import { SCENARIOS, tada } from "./formatters.js";

export const SOURCE_LABEL = {
  sample: { label: "SAMPLE DATA", tone: "warning", hint: "Canned listings, not scraped" },
  apify_cached: { label: "CACHED APIFY", tone: "warning", hint: "Saved real scrape, not fetched live for this deal" },
  apify: { label: "LIVE APIFY", tone: "success", hint: "Scraped live for this deal" },
};

export const PROVENANCE = {
  codex: { label: "CODEX SUBSCRIPTION", tone: "info", hint: "Written by Codex using the signed-in ChatGPT subscription" },
  scripted: { label: "SCRIPTED", tone: "neutral", hint: "Scripted persona, not a language model" },
  fallback: { label: "SCRIPTED FALLBACK", tone: "warning", hint: "The model call failed; a scripted line was used instead" },
  guard: { label: "GUARD", tone: "danger", hint: "Spoken after the wallet guard's decision, not by the model" },
};

export function provenanceOf(e) {
  if (e.type !== "negotiation") return null;
  const d = e.data;
  if (d.backend === "guard") return "guard";
  if (d.backend === "codex") return "codex";
  if (d.fallback_reason) return "fallback";
  // Older seller events predate backend provenance and were always scripted.
  return d.backend === "mock" || (d.speaker === "viktor" && d.backend == null) ? "scripted" : null;
}

const failedChecks = (d) => Object.entries(d.checks ?? {}).filter(([, v]) => !v).map(([k]) => k.replaceAll("_", " "));

// -> { title, description, tone } or null to leave the event out of the timeline.
export function describeEvent(e) {
  const d = e.data;
  switch (e.type) {
    case "task_created": {
      const s = SCENARIOS[d.demo_mode];
      return { title: "Task created", description: `${s ? s.name : d.demo_mode} · budget ${tada(d.budget)}`, tone: "neutral" };
    }
    case "negotiation": return { title: "Negotiation started", description: "Max and Viktor are haggling over the price.", tone: "info" };
    case "quote": return { title: "Price agreed", description: tada(d.price), tone: "info" };
    case "needs_approval": return { title: "Human approval requested", description: `${tada(d.price)} · ${d.reason}`, tone: "warning" };
    case "approved": return { title: "Approved by a human", description: tada(d.price), tone: "success" };
    case "blocked": return { title: "Payment blocked", description: d.reason ?? "Blocked by the wallet guard.", tone: "danger" };
    case "escrow_locked":
      return { title: "Escrow locked", description: `Wallet guard allowed ${tada(d.price)}; funds are held in escrow.`, tone: "success" };
    case "already_paid":
      return { title: "Already paid, not paid again", description: `Deal found paid after a restart (${tada(d.price)}).`, tone: "info" };
    case "delivered": {
      const src = SOURCE_LABEL[d.source];
      return { title: "Delivery received", description: `${d.items ?? 0} listings${src ? ` · ${src.label}` : ""}`, tone: "info" };
    }
    case "verified":
      return d.ok
        ? { title: "Verification passed", description: "All delivery checks passed.", tone: "success" }
        : { title: "Verification failed", description: `Failed: ${failedChecks(d).join(", ") || "unknown check"}`, tone: "danger" };
    case "released":
      return d.release === "scheduled"
        ? { title: "Release scheduled", description: `${tada(d.price)}${d.settles_at ? ` settles ${d.settles_at}` : ""}; not yet settled on-chain.`, tone: "success" }
        : { title: "Payment released", description: `${tada(d.price)} released to Viktor.`, tone: "success" };
    case "refunded": return { title: "Escrow refunded", description: `${tada(d.price)} returned to Max.`, tone: "warning" };
    case "walked_away": return { title: "Negotiation ended", description: d.reason ?? "A party walked away.", tone: "neutral" };
    case "controls_updated":
      return { title: "Controls changed", description: Object.entries(d).map(([k, v]) => `${k.replaceAll("_", " ")}: ${v}`).join(", "), tone: "info" };
    case "error": return { title: "Error", description: d.message ?? "Something went wrong.", tone: "danger" };
    default: return null; // balances and unknown future events stay out of the readable timeline
  }
}
