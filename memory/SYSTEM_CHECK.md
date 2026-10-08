# Integrated system check — 2026-10-08/09

## I01–I06 completion — 2026-10-09 00:42 +02:00

- Isolated I-only staged source export also passes all 390 backend tests on Python 3.13 (36.90s) and 3.11 (30.41s). This excludes the concurrent R/video edits; snapshot: backend/data/i-staged-501319f3/source/.

- I04 now supports subscription Viktor via optional SELLER_LLM_MODE=codex; defaults preserve the scripted-seller rehearsal profile. No API keys or new payment integration.
- Real Viktor checker produced opening 18 and accepted 7 without fallback. Full two-agent HTTP Act 1 used three Max and four Viktor Codex turns, 20 genuine cached Apify listings and seven new ElevenLabs clips; no model/voice fallback, SIMULATED release in 42.2s.
- Strict seller outputs, floor/agreement enforcement, same-round retry deduplication, stale-round conflicts, cancellation and staged-con isolation have regression coverage. Buyer forwards actual seller provenance; its HTTP deadline allows seller CLI cleanup/fallback.
- Shared-workspace validation: 392 backend tests on Python 3.13 (36.25s) and Python 3.11 (27.54s), including two concurrent R-path staging regressions. Frontend: 33 tests and build pass; rendered Edge checks cover live/fallback/legacy seller labels, both-agent usage and mixed-mode header, with zero page errors.
- Evidence under backend/data/: i-complete-97ac1034/ (fresh live deal, seven clips, events/report), hour-seller-ui-report.json (rendered labels). Existing .env, ledgers and parallel R/video work are preserved. I04 is opt-in; changing the final video profile requires its own R02 rehearsal.

## Scoped audit — 2026-10-09, closed when the user returned

Scope: existing Ziya data, subscription-agent, voice and integration paths. Murad's
launcher and follow-up audit commits through 3b10519 are integrated and revalidated;
Mais's active funding branch is retained. The planned 50-minute endurance run stopped
after 20m55s when the user returned. Only completed checks are counted below.

| Check | Result |
|---|---|
| Backend | 364 passed on Python 3.13 (28.84s) and fresh Python 3.11 (33.05s), including Murad's latest bounds/CORS changes |
| Frontend / browser | 32 tests; production build; 11 fresh Edge dashboard scenarios pass with zero page errors |
| Live providers | Three real subscription Codex turns, 20 genuine cached Apify flats, seven new ElevenLabs MP3s; SIMULATED release in 21.8s, no text fallbacks |
| Voice playback | Real Edge MP3 playback: order, replay dedupe, reset identities, missing clip skip, Stop/Mute, destroy and watchdog pass; maximum one clip playing |
| Clean checkout | No .env/cache/dependencies initially; npm start installs dependencies, starts all three services and completes a sample-data SIMULATED deal |
| Terminal | Ten real-HTTP scenarios pass: honest, con, junk, latest-deal replay, approve, replay approved, decline, replay declined, paused and offline |
| Endurance | 21 cycles in 1255.2s; 63 refunds, 44 blocked, 21 walkaways, seven releases; five concurrent batches and one corrupted-cache refund; zero failures |
| Recovery during endurance | One actual crash after funding recovered with exactly one lock; two pending-approval restarts preserved consent; seller remained running |
| Endurance cleanup | Zero pending tasks/approvals/SSE subscribers; balances 51 buyer / 49 seller / 0 escrow, conserving 100; only the audit's owned processes were stopped |

Fixes: repeated Codex cancellation and process cleanup; bounded model/MP3 output;
strict cached records and run identity; seller response/deal/round/job/price binding;
failed jobs cannot release with stale results; invalid legacy tasks preserve their
rows and cannot stop valid recovery; terminal replay ignores old deals and stale
approvals. Strict integer rents prevent seller-response coercion; malformed URL ports
and control characters fail verification. Tests now default to LEDGER_PATH=:memory:
even without a shell override.

Local evidence under backend/data/: hour-clean-start-2929d7ee/,
hour-cli-125ea4c3/, hour-voice-browser-report.json, system-live-91702a89/,
system-dashboard-0bb1bbaa/ (latest team-commit browser check), system-dashboard-41ade425/
(earlier check), and hour-endurance-97549284/ (stopped on return, not a 50-minute pass).
All payment tests are SIMULATED or use the fake Masumi node. No new paid Apify run.
Endurance deliberately exercised unavailable-Codex/text fallbacks; it does not complete
three consecutive full-profile live-provider rehearsals. That remains R02 in plan.md.

## Earlier integrated audit

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
