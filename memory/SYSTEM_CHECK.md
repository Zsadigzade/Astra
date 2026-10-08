# Integrated system check — 2026-10-08

Audited main at 8a24b38, including Murad's dashboard/operator controls, Mais's Masumi schema fix,
and Ziya's subscription, data, voice, ledger and runner changes. Origin was fetched again before
completion; no newer team commits were present. Fixes and this report are committed together.

## Final verification

| Check | Result |
|---|---|
| Complete backend suite | 255 passed (16.74s), isolated LEDGER_PATH=:memory: |
| Frontend suite / production build | 32 passed / build passed |
| Fresh browser scenarios | Honest release; staged con blocked; junk refunded; approval accepted and declined |
| Dashboard controls | Pause/resume, paused task rejection, runtime rounds, visible request failures |
| Browser resilience | Actual buyer stop/restart, SSE replay without duplicate transcript, theme persistence, no horizontal overflow at 390/1000/1440px; zero page errors |
| Actual runner crash recovery | One lock, one staged buyer restart, seller survives, one already_paid event, one release; SIMULATED balances 93/7/0 |
| Actual reset | Configured completed ledger archived byte-for-byte; new ledger empty; only owned processes stopped |
| Subscription access | Live Codex checker passes; fresh Act 1 uses three Codex turns, settles at 7 |
| Apify | GET-only recovery returns 20 valid listings from ZNboU2b0EHUJgFaEQ; no new paid scrape |
| ElevenLabs | Voice discovery and two new samples pass; fresh Act 1 generates and serves seven MP3s with no text fallbacks |
| Integrated live-provider Act 1 | 20 cached genuine listings verified, SIMULATED escrow released in 22.8s |
| Hosted Masumi | Health passes; authenticated /payment-source returns 401 with current local configuration |

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

## Limits and evidence

All payment rehearsals above used SIMULATED money or the test Masumi service. Live Preprod
escrow, wallet funding, Viktor registration and every-laptop acceptance are not verified.
The user is checking the hosted ADMIN_KEY against local MASUMI_API_KEY; no secrets were logged.
Existing application ledgers, .env and unrelated running services were preserved.

Ignored local artifacts: system-dashboard-feea8ead/ (11 browser checks/screenshots),
system-runner-audit-6872233b/ (crash/reset report), system-live-ca49c10c/ (fresh live-provider deal),
and system-check-20261008/ (recovered data and voice samples). These paths are relative to backend/data/.
Earlier isolated attempts retained their own ledgers: an intermediate verifier rejected valid suffixes;
the final corrected code passes both sample and genuine cached data. Only final runs are counted above.
