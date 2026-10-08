# Handoff — integrated main

updated: 2026-10-09 01:45 +02:00 · I13/I14 completion, validation scope and parallel ownership reconciled

## I13 subscription runtime handoff — local working tree

- I13 is complete: each buyer/seller service limits concurrent Codex turns across deals (default 2), bounds queue waiting (5s within the existing 30s turn deadline), and applies a local cooldown after repeated CLI failures (3 failures, 15s). One subsequent turn probes recovery; success restores subscription turns. Queue/cooldown fallback remains visibly scripted; guard and seller floor remain authoritative.
- Cancelled waiters start no subprocess. Running cancellation holds its slot until child-tree cleanup finishes; late results from before cooldown cannot incorrectly restore availability. These limits do not predict provider quota resets and add no API-token access.
- Validation: **145 focused tests passed**, then **523 full backend tests passed in 51.99s** on the shared working-tree snapshot. Coverage includes six real local Python child processes capped at two, repeated cancellation, both agents' fallback labels and recovery probes. No live inference, synthesis, scraping, payments or service restarts were used for I13 acceptance.
- Settings and reproduction commands: [runtime status](status/i13-runtime.md), [interfaces](INTERFACES.md), [system check](SYSTEM_CHECK.md). I07–I12 remain with the parallel data/voice owner. The prior R02/R05 profile still needs affected-change rehearsal before recording; these tests do not complete release/video/live-payment gates.

## I14 readiness handoff — local working tree

- I14 is complete: from `backend/`, run `uv run python scripts/readiness.py`. It reports selected agent modes, Codex/ChatGPT sign-in, exact rental-cache match/provenance and stale override, voice configuration, and writable audio storage. Missing prerequisites exit nonzero with actions to take.
- Defaults start no Actor runs, synthesize no speech and move no money. `--live-probe` explicitly invokes existing bounded checks for enabled subscription agents and configured voices (voice credits); no live probes were run in this session. A pass is not live escrow or full E2E acceptance.
- Verification at completion: **62 focused tests passed**, including 30 readiness tests. The actual local profile check exited 0 for subscription Max, scripted Viktor, 20 cached real rentals and configured ElevenLabs. Provider access/quota and synthesis remain untested by the default command. Evidence and reproduction: [readiness status](status/readiness.md), [system check](SYSTEM_CHECK.md).
- These results describe the working-tree snapshot tested by this session, not a final-revision audit or a re-rehearsal of subsequent parallel changes. I07–I12 belong to the owner in [ziya status](status/ziya.md); I13 belongs to [runtime status](status/i13-runtime.md). Preserve their edits and consult their latest acceptance reports.

## Go-live preflight (added 2026-10-09, samir/claude; uncommitted)
- New: `npm run setup`, `npm run doctor`, `npm run doctor:live` (`backend/scripts/doctor.py`): per-integration readiness, no secrets printed.
- Verified on this laptop: Codex CLI signed in and working (`LLM_MODE=codex`); the honest deal ran with genuine Codex Max lines and released;
  the dashboard shows "Codex subscription" + "VIKTOR SCRIPTED" when SELLER_LLM_MODE=mock (Viktor can now also run on Codex; see SELLER_LLM_MODE). The staged con act intentionally keeps a scripted Max (label: mock).
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
- [plan.md](../plan.md): 23 completed items moved to [the archive](archive/COMPLETED.md); the 27-item follow-up checklist now has I13/I14 complete and 25 open items. I07–I12 remain in progress with the data/voice owner; status files carry acceptance evidence. [Video package](../video/README.md) contains a 1:55 script, evidence storyboard, draft captions and capture/export handoff. Full reachable-history scan and public repository check passed for the earlier baseline; rerun at final revision. Remaining: every-laptop startup, affected-profile/timed video rehearsal, live-chain gates, recording/edit/export and submission. I01–I06 are complete; optional subscription Viktor is verified but needs its own R02 rehearsal if selected for recording.
- Hosted node: Railway mellow-energy, masumi-payment-service + masumi-psql-database; base https://masumi-payment-service-production-96e0.up.railway.app/api/v1. Upstream Dockerfile fix is in Zsadigzade/masumi-payment-service ce8cfdb5 (see TRAPS).
- No live escrow proof by 01:00 means SIMULATED video; feature freeze 04:00, video/repo 06:30, target submission 07:00, deadline 07:14 Prague time.
- Act 4 refund remains SIMULATED. Real release is scheduled, not immediate. Seller jobs are in memory: never restart seller mid-deal.
- Local rehearsal modes remain codex/cached/elevenlabs/simulated. Secrets stay in ignored .env; Codex retains its own login. No existing ledger or unrelated service was changed during the audit.
- Local main includes the prior verified consolidation; a new remote Mais branch records pending faucet funding and is retained for its owner's ongoing work. Legacy generated root folders are archived under ignored backend/data/legacy-workspace/.
