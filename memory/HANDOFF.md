# Handoff — integrated main

updated: 2026-10-09 00:24 · ziya · scoped hour audit in progress

## Go-live preflight (added 2026-10-09, samir/claude; uncommitted)
- New: `npm run setup`, `npm run doctor`, `npm run doctor:live` (`backend/scripts/doctor.py`): per-integration readiness, no secrets printed.
- Verified on this laptop: Codex CLI signed in and working (`LLM_MODE=codex`); the honest deal ran with genuine Codex Max lines and released;
  the dashboard shows "Codex subscription" + "VIKTOR SCRIPTED". The staged con act intentionally keeps a scripted Max (label: mock).
- 2026-10-09 00:50 (samir laptop): live Apify scrape OK (run LtcCqpY0nOPVlYmtt, 20 real Praha 7 rentals saved to backend/data/flats-apify.json, git-ignored); `.env` has APIFY_MODE=cached + LLM_MODE=codex. Full deal with real Codex Max + `apify_cached` data released (SIMULATED money). Voice and Masumi still off here.
- 2026-10-09 01:15 (samir laptop): ElevenLabs live. Key is restricted (no voices_read/models_read), so `voice_check.py` cannot list voices but text-to-speech works; voices are premade Antoni (Max, ErXwobaYiN019PkySvjV) and Arnold (Viktor, VR6AewLTigWG4xSOukaG). A full deal voiced 7/7 lines, 383 characters (~400 of 10,000 free credits). `doctor:live` now falls back to a tiny speech probe. Audible playback not confirmed in headless; listen once in a real browser.
- Not live here: Apify (no token), ElevenLabs (no key/voices), Masumi (no node key/agent/vkey). They need the keys from Ziya's .env, shared out of band.
- Track fit (Agentic Economy: discovery, transactions, payments, wallets, dispute resolution): payments, wallets (guard + escrow) and
  transactions exist. **Agent discovery** (the seller URL is configured, not looked up in the Masumi registry) and **dispute resolution**
  (only the dispute-window timestamp is passed through; no flow or UI) are not built. State that in the video and README limitations.

## General requests (added 2026-10-09, samir/claude; uncommitted)
- Request box in the dashboard + `POST /requests/parse` (`backend/app/core/intent.py`). The job (count, Praha 1-22, rent cap) now drives Max's prompt,
  Viktor's opening line, sample data, the Apify scrape (`location: Praha N`) and the verifier. Bounds enforced on the network (count 1-100).
- Live-verified here: "4 flats in Prague 2 under 30k" -> parsed, real Apify scrape for Praha 2 (LIVE APIFY), real Codex Max, all 4 checks passed, released (SIMULATED money).
- `.env` on this laptop: LLM_MODE=codex, APIFY_MODE=apify, TTS_MODE=elevenlabs, PAYMENTS_MODE=simulated. A live scrape for a different request does NOT overwrite the saved demo cache.

## Current verification
- I-path audit: 344 backend tests pass on Python 3.13 and fresh Python 3.11; fresh live Codex/cached-data/seven-clip Act 1 and browser scenarios pass. Fixes cover cancellation, cache/voice validation, bounded TTS, seller-response binding and strict delivery validation; invalid legacy tasks no longer block other recovery. A 50-minute endurance run is in progress; final results will be recorded in SYSTEM_CHECK.md.
- Terminal replay now follows the latest deal and suppresses stale approvals; 10 real-HTTP CLI scenarios pass. Tests default to an in-memory ledger.
- Audited team commits through 8a24b38 plus fixes recorded in [SYSTEM_CHECK.md](SYSTEM_CHECK.md). Murad's UI update 2d0d987 also passed merged frontend/browser revalidation; its API-era scripted-mode label was corrected for subscription Codex.
- 255 backend tests, 32 frontend tests and production build pass. Eleven fresh HTTP/Edge browser checks pass with zero page errors: honest release, con block, refund, approval/decline, controls, offline/reconnect, theme and responsive widths.
- Actual runner rehearsal: one staged buyer crash, one restart, seller survives, one lock, one recovery and one release at 7; SIMULATED balances 93/7/0. Reset preserves the original ledger byte-for-byte and starts empty.
- Fresh live-provider Act 1: three Codex turns, 20 genuine cached Apify listings verified, seven new ElevenLabs clips served, SIMULATED release in 22.8s. Earlier merged-dashboard replay played five saved clips once in order without overlap.
- Hosted Railway Masumi now passes health, authentication and Preprod source checks. Full local readiness fails on missing MASUMI_AGENT_ID and missing/invalid SELLER_VKEY; registration, wallet funding and live escrow remain unverified.

## Audit fixes
- Lost payment replies retain paying intent for idempotent restart; buyer shutdown cancels owned work before closing HTTP resources and preserves pending approvals.
- Guard blocks nonfinite amounts/budgets/limits; API budgets must be positive and finite. Verifier rejects false district matches, nonpositive rents and malformed URLs while accepting real locality suffixes.
- Masumi only reports scheduled release after confirmed result submission/release state; funded errors remain recoverable. Provider error bodies are omitted from dashboard/log diagnostics.
- Dashboard handles offline pause failures, preserves honest labels and keeps scheduled releases/funded errors in escrow totals. Budget meter uses the current task; lifetime totals are labelled.
- Runner reads declared service ports consistently. Details/regressions are in SYSTEM_CHECK.md and TRAPS.md.

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
- [plan.md](../plan.md) remains the task checklist; single-laptop success does not complete every-laptop or live-chain gates. Ziya owns I01-I06; Mais reports local node readiness, pending funding/registration; Murad's status file has no newer owner update.
- Hosted node: Railway mellow-energy, masumi-payment-service + masumi-psql-database; base https://masumi-payment-service-production-96e0.up.railway.app/api/v1. Upstream Dockerfile fix is in Zsadigzade/masumi-payment-service ce8cfdb5 (see TRAPS).
- No live escrow proof by 01:00 means SIMULATED video; feature freeze 04:00, video/repo 06:30, target submission 07:00, deadline 07:14 Prague time.
- Act 4 refund remains SIMULATED. Real release is scheduled, not immediate. Seller jobs are in memory: never restart seller mid-deal.
- Local rehearsal modes remain codex/cached/elevenlabs/simulated. Secrets stay in ignored .env; Codex retains its own login. No existing ledger or unrelated service was changed during the audit.
- Local main includes the prior verified consolidation; a new remote Mais branch records pending faucet funding and is retained for its owner's ongoing work. Legacy generated root folders are archived under ignored backend/data/legacy-workspace/.
