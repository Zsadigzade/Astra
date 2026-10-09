export const fmt = (v, digits = 2) =>
  v == null || Number.isNaN(Number(v)) ? "-" : Number(v).toLocaleString(undefined, { maximumFractionDigits: digits });

export const tada = (v, digits = 2) => (v == null ? "-" : `${fmt(v, digits)} tADA`);

export const clock = (ts) =>
  new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const shortId = (id, n = 6) => (id ? String(id).slice(-n) : null);

// Only ever link to http(s); event data is not trusted to be a safe URL.
export const safeUrl = (u) => (typeof u === "string" && /^https?:\/\//i.test(u) ? u : null);

export const SCENARIOS = {
  honest: { n: 1, mode: "honest", name: "Normal request", purpose: "Max negotiates, the guard pays, you get the data", staged: false,
    explain: "Max haggles Viktor down to a fair price, the wallet guard lets payment through, escrow locks, the delivery is verified and funds are released." },
  con: { n: 2, mode: "con", name: "The Con", purpose: "Unsafe agreement blocked by the wallet guard", staged: true,
    explain: "Viktor fakes a manager approval and Max falls for it. The guard still refuses: the price is over the hard cap, so no money moves." },
  recovery: { n: 3, mode: "recovery", name: "Recovery", purpose: "Buyer restarts without paying twice", staged: true, terminalOnly: true,
    explain: "The buyer crashes right after locking escrow. On restart it finds the deal already paid and finishes without paying again." },
  junk: { n: 4, mode: "junk", name: "The Refund", purpose: "Invalid delivery fails verification and is refunded", staged: true,
    explain: "Viktor delivers garbage. The rule-based verifier rejects it and the escrow is refunded to Max." },
};
export const EXAMPLES = [
  "Find me 20 flats in Praha 7 under 25,000 CZK",
  "10 apartments in Prague 2, max 30k",
  "Explain in two sentences why escrow protects buyers",
];

export const SCENARIO_LIST = [SCENARIOS.honest, SCENARIOS.con, SCENARIOS.recovery, SCENARIOS.junk];
export const RECOVERY_COMMAND = "cd backend && uv run python scripts/up.py --crash";
export const BACKEND_COMMAND = "cd backend && uv run python scripts/up.py";
