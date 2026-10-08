# Handoff — integrated main

updated: 2026-10-09 00:30 · ziya · audit closed after user returned; checklist reconciled

## Current verification
- Latest main through Murad's 3b10519: 364 backend tests pass on Python 3.13 and fresh Python 3.11; 32 frontend tests, production build and 11 fresh Edge scenarios pass with zero page errors. Full evidence: [SYSTEM_CHECK.md](SYSTEM_CHECK.md).
- Timed audit stopped when the user returned: 20m55s, 21 cycles, 135 terminal outcomes, five concurrent batches, one actual funded crash/recovery and two approval/restarts; no failures, duplicate payments or pending tasks/approvals/subscribers. Final SIMULATED balances 51/49/0. The planned 50 minutes were not completed.
- Terminal replay now follows the latest deal and suppresses stale approvals; 10 real-HTTP CLI scenarios pass. Tests default to an in-memory ledger.
- Murad's latest input bounds, local-origin CORS and offline payment-status changes are integrated and revalidated; his single-command launcher passed fresh-checkout acceptance.
- Actual runner rehearsal: one staged buyer crash, one restart, seller survives, one lock, one recovery and one release at 7; SIMULATED balances 93/7/0. Reset preserves the original ledger byte-for-byte and starts empty.
- Fresh live-provider Act 1: three Codex turns, 20 genuine cached Apify listings verified, seven new ElevenLabs clips served, SIMULATED release in 21.8s. Real Edge playback, replay/reset, Stop/Mute and stalled/missing clips pass.
- Hosted Railway Masumi now passes health, authentication and Preprod source checks. Full local readiness fails on missing MASUMI_AGENT_ID and missing/invalid SELLER_VKEY; registration, wallet funding and live escrow remain unverified.

## Audit fixes
- Lost payment replies retain paying intent for idempotent restart; buyer shutdown cancels owned work before closing HTTP resources and preserves pending approvals.
- Guard blocks nonfinite amounts/budgets/limits; API budgets must be positive and finite. Verifier rejects false district matches, nonpositive rents and malformed URLs while accepting real locality suffixes.
- Masumi only reports scheduled release after confirmed result submission/release state; funded errors remain recoverable. Provider error bodies are omitted from dashboard/log diagnostics.
- Dashboard handles offline pause failures, preserves honest labels and keeps scheduled releases/funded errors in escrow totals. Budget meter uses the current task; lifetime totals are labelled.
- Runner reads declared service ports consistently. Details/regressions are in SYSTEM_CHECK.md and TRAPS.md.
- Scoped audit also fixed repeated Codex cancellation, cache coercion, oversized TTS, cross-deal/job replies, invalid legacy recovery and malformed delivered rents/URLs.

## What works
- The Haggle: buyer Max (:8000, backend/app/buyer) negotiates with seller Viktor (:8001, backend/app/seller), wallet guard locks escrow, verifier checks delivery, then release/refund. Dashboard consumes SSE /events.
- Backend commands run from backend/: uv run python scripts/up.py [--reset] [--crash]; terminal scripts/act.py honest|con|junk. Murad's launcher update makes root npm start run backend and dashboard; npm run web/api select one side. Fresh checkout installed dependencies, started all three services and completed a credential-free SIMULATED deal.
- All four acts work in SIMULATED mode. Guard cap 10, budget 20, approval above 8; staged con at 25 is blocked. Restart never pays an already-funded deal twice.
- Permanent subscription-only access: LLM_MODE=codex uses local ChatGPT-authenticated Codex CLI with labelled scripted fallback. No OpenAI API token or SDK. Viktor and STAGED Act 2 Max remain scripted.
- Genuine data: swerve/sreality-scraper; Praha 7/monthly-CZK validation, provenance and matching apify_cached fallback. GET-only scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ restores the 20-listing cache without another paid run.
- Voice: ElevenLabs Brian/Callum; bounded text fallback; one ordered Play/Stop/Mute queue, reset-safe identities and 10s stalled-clip watchdog.
- Dashboard: light/dark theme, event-derived state, runtime controls. Cap adjustable within configured GUARD_CAP; pause rejects new tasks with HTTP 423, in-flight deals finish. Round budget captured per negotiation.
- Ledger binds payment mode before recovery. Separate files required for simulated and real payments; mixed or ambiguous historical activity fails closed.
- Safe reset archives the configured completed simulated ledger; refuses unfinished deals, held escrow, real/mixed history and SQLite sidecars. Runner refuses occupied ports and cleans up its own children only.
- Masumi adapter supports Dynamic pricing, idempotent purchase and scheduled release; checker accepts paymentSourceType/paymentType. Automated adapter checks use the fake node.

## Team and release gates
- [plan.md](../plan.md): 18/35 items complete. Remaining: every-laptop startup, three full-profile rehearsals, 1080p recording acceptance, live-chain gates, video and submission. I04 (live Viktor) remains optional; current scripted Viktor works.
- Hosted node: Railway mellow-energy, masumi-payment-service + masumi-psql-database; base https://masumi-payment-service-production-96e0.up.railway.app/api/v1. Upstream Dockerfile fix is in Zsadigzade/masumi-payment-service ce8cfdb5 (see TRAPS).
- No live escrow proof by 01:00 means SIMULATED video; feature freeze 04:00, video/repo 06:30, target submission 07:00, deadline 07:14 Prague time.
- Act 4 refund remains SIMULATED. Real release is scheduled, not immediate. Seller jobs are in memory: never restart seller mid-deal.
- Local rehearsal modes remain codex/cached/elevenlabs/simulated. Secrets stay in ignored .env; Codex retains its own login. No existing ledger or unrelated service was changed during the audit.
- Local main includes the prior verified consolidation; a new remote Mais branch records pending faucet funding and is retained for its owner's ongoing work. Legacy generated root folders are archived under ignored backend/data/legacy-workspace/.
