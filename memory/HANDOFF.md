# Handoff — integrated main

updated: 2026-10-09 01:30 · active plan and completed archive reconciled

## Current verification
- R02/R05 complete: three consecutive runs per act plus approval/decline, 35 Codex turns and 100 speech clips with no fallback; three actual buyer crashes recover with one payment each. Sixteen 1920×1080 screenshots pass framing checks and representative visual review. Final simulated balances 49/51/0; all owned services stopped. Evidence: backend/data/r-rehearsal-29b87432/. Reproduce with backend/scripts/rehearse.py; profile remains subscription Max / scripted Viktor / cached Apify / ElevenLabs / SIMULATED.
- I04: optional SELLER_LLM_MODE=codex uses the existing isolated CLI for Viktor, with floor/offer checks, retry/cancellation protection and honest fallback labels. Live Act 1: three Max + four Viktor Codex turns, 20 real cached flats, seven speech clips, no fallback, SIMULATED release in 42.2s. Default seller stays mock for the current rehearsal profile.
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
- Permanent subscription-only access: LLM_MODE=codex and optional SELLER_LLM_MODE=codex use local ChatGPT-authenticated CLI for Max/Viktor, with labelled fallback. No API token or SDK. Both STAGED Act 2 agents and seller accept/walk acknowledgements remain scripted.
- Genuine data: swerve/sreality-scraper; Praha 7/monthly-CZK validation, provenance and matching apify_cached fallback. GET-only scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ restores the 20-listing cache without another paid run.
- Voice: ElevenLabs Brian/Callum; bounded text fallback; one ordered Play/Stop/Mute queue, reset-safe identities and 10s stalled-clip watchdog.
- Dashboard: light/dark theme, event-derived state, runtime controls. Cap adjustable within configured GUARD_CAP; pause rejects new tasks with HTTP 423, in-flight deals finish. Round budget captured per negotiation.
- Ledger binds payment mode before recovery. Separate files required for simulated and real payments; mixed or ambiguous historical activity fails closed.
- Safe reset archives the configured completed simulated ledger; refuses unfinished deals, held escrow, real/mixed history and SQLite sidecars. Runner refuses occupied ports and cleans up its own children only.
- Masumi adapter supports Dynamic pricing, idempotent purchase and scheduled release; checker accepts paymentSourceType/paymentType. Automated adapter checks use the fake node.

## Team and release gates
- [plan.md](../plan.md): 23 completed items moved to [the archive](archive/COMPLETED.md); 12 unfinished items retained and 15 follow-ups listed, including eight proposed I-path features (I07–I14) with acceptance criteria; these features are not implemented. [Video package](../video/README.md) contains a 1:55 script, evidence storyboard, draft captions and capture/export handoff. Full reachable-history scan and public repository check pass with reviewed run-ID false positives; rerun at final revision. Remaining: every-laptop startup, timed video rehearsal, live-chain gates, recording/edit/export and submission. I01–I06 are complete; optional subscription Viktor is verified but needs its own R02 rehearsal if selected for recording.
- Hosted node: Railway mellow-energy, masumi-payment-service + masumi-psql-database; base https://masumi-payment-service-production-96e0.up.railway.app/api/v1. Upstream Dockerfile fix is in Zsadigzade/masumi-payment-service ce8cfdb5 (see TRAPS).
- No live escrow proof by 01:00 means SIMULATED video; feature freeze 04:00, video/repo 06:30, target submission 07:00, deadline 07:14 Prague time.
- Act 4 refund remains SIMULATED. Real release is scheduled, not immediate. Seller jobs are in memory: never restart seller mid-deal.
- Local rehearsal modes remain codex/cached/elevenlabs/simulated. Secrets stay in ignored .env; Codex retains its own login. No existing ledger or unrelated service was changed during the audit.
- Local main includes the prior verified consolidation; a new remote Mais branch records pending faucet funding and is retained for its owner's ongoing work. Legacy generated root folders are archived under ignored backend/data/legacy-workspace/.
