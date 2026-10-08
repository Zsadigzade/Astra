# Integrated system check — 2026-10-08

Audited main at 8a24b38, including Murad's dashboard/operator controls, Mais's Masumi schema fix,
and Ziya's subscription, data, voice, ledger and runner changes. Murad's UI update 2d0d987 arrived
before push; it was merged with the audit fixes and passed fresh frontend/browser revalidation.
Fixes and this report are committed together.

## Final verification

| Check | Result |
|---|---|
| Complete backend suite | 255 passed (16.74s), isolated LEDGER_PATH=:memory: |
| Frontend suite / production build | 32 passed / build passed |
| Fresh browser scenarios | Honest release; staged con blocked; junk refunded; approval accepted and declined |
| Dashboard controls | Pause/resume, paused task rejection, runtime rounds, visible request failures |
| Browser resilience | Actual buyer stop/restart, SSE replay without duplicate transcript, theme persistence, no horizontal overflow at 390/1000/1100/1440px; zero page errors |
| Actual runner crash recovery | One lock, one staged buyer restart, seller survives, one already_paid event, one release; SIMULATED balances 93/7/0 |
| Actual reset | Configured completed ledger archived byte-for-byte; new ledger empty; only owned processes stopped |
| Subscription access | Live Codex checker passes; fresh Act 1 uses three Codex turns, settles at 7 |
| Apify | GET-only recovery returns 20 valid listings from ZNboU2b0EHUJgFaEQ; no new paid scrape |
| ElevenLabs | Voice discovery and two new samples pass; fresh Act 1 generates and serves seven MP3s with no text fallbacks |
| Integrated live-provider Act 1 | 20 cached genuine listings verified, SIMULATED escrow released in 22.8s |
| Latest UI subscription/audio replay | Codex, cached-data and SIMULATED labels visible; five saved MP3s play once in order without overlap/media/page errors; controls pass |
| Hosted Masumi | Final node-only check passes health, authentication and one Preprod Cardano payment source |
| Local seller readiness | Fails: MASUMI_AGENT_ID missing; SELLER_VKEY missing/invalid; registration and wallet setup still needed |

## Defects fixed

- Preserve payment intent after a lost lock response so restart resolves the same payment instead of abandoning potentially funded work.
- Reject nonfinite money/guard values and nonpositive/nonfinite task budgets.
- Reject misleading district matches (Praha 70), nonpositive rent and malformed URLs; accept sample and genuine Apify locality suffixes.
- Require confirmed Masumi result submission/release state before reporting scheduled release; otherwise keep escrow recoverable.
- Cancel buyer-owned tasks before closing HTTP resources on shutdown; preserve pending approval for restart.
- Keep provider response bodies out of Masumi errors surfaced through logs/dashboard events.
- Use declared runner service ports consistently for startup and restart checks.
- Handle pause failures visibly, disable offline pause controls, and preserve simulation labels during disconnects.
- Keep funded errors and scheduled releases in escrow totals; distinguish scheduled from completed release and current-task budget from lifetime usage.
- Preserve the latest UI layout while correcting its API-era mode check so subscription Codex is not labelled SCRIPTED AGENTS; scripted seller identity remains explicit.

## Limits and evidence

All payment rehearsals above used SIMULATED money or the test Masumi service. Live Preprod
escrow, wallet funding, Viktor registration and every-laptop acceptance are not verified.
Initial hosted access returned 401; the final recheck passes with the current local configuration.
No secrets were logged. The remaining configuration blockers are MASUMI_AGENT_ID and SELLER_VKEY.
Existing application ledgers, .env and unrelated running services were preserved.

Ignored local artifacts: system-dashboard-4bd095d7/ (final merged UI browser checks/screenshots),
system-runner-audit-6872233b/ (crash/reset report), system-live-ca49c10c/ (fresh live-provider deal),
system-check-20261008/ (recovered data and voice samples), and i-path-smoke-d2448b5d/ (latest UI subscription/audio replay). These paths are relative to backend/data/.
Earlier isolated attempts retained their own ledgers: an intermediate verifier rejected valid suffixes;
the final corrected code passes both sample and genuine cached data. Only final runs are counted above.
