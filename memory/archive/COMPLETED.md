# Completed checklist archive

Archived: **2026-10-09 00:58 Prague time** from the checklist at `f4a87de`.

These **23 completed items** retain their original IDs and acceptance notes. This is a
historical snapshot, not a claim that every laptop, live Preprod payments or video export
has passed. Later final-revision checks belong in the [active plan](../../plan.md).
Evidence: [system checks](../SYSTEM_CHECK.md) and [video release audit](../../video/release-audit.md).
Local evidence under `backend/data/` is ignored by Git; its paths are relative to the repository root.


## Existing baseline

- [x] **B01** Buyer and seller HTTP services, negotiation, wallet guard and verifier exist.
- [x] **B02** Four acts verified in SIMULATED mode; automated coverage includes approval, crash recovery and adversarial deliveries. I-completion suite: 390 tests on Python 3.11/3.13; shared workspace also passes two pending R-path regressions (392 total).
- [x] **B03** Masumi adapter and seller payment flow implemented and tested against a fake node; readiness checker supports `--node-only`.
- [x] **B04** Scripted negotiation works; subscription Codex replaces the API-key runtime, with explicit fallback labels and independent wallet guard.
- [x] **B05** Full dashboard consumes SSE, starts acts 1/2/4, displays balances, guard decisions and approvals; pause/limits, themes and ordered audio work. 33 frontend tests and production build pass.

## Startup and dashboard

- [x] **D02** Replace the dashboard stub with two avatars, readable chat bubbles, balances and a clear event timeline. Implemented and browser-tested.
- [x] **D03** Show persistent **SIMULATED** and **STAGED** labels where applicable, sample/cached data provenance, a red blocked guard state and clear approval/decline controls. Verified in Edge.
- [x] **D04** Verify dashboard act selection and complete acts 1, 2 and 4 from the UI. Honest release, con blocked and junk refund pass, as do approval/decline and offline/reconnect.

## Masumi payments

- [x] **M01** Bring up the hosted Railway/Blockfrost Preprod node and pass `uv run python scripts/masumi_check.py --node-only`. Hosted health, authentication and Preprod payment-source checks passed; the earlier 401 is resolved.

## Data, agents and voice

- [x] **I01** Select an Apify actor for Praha 7 rentals and implement `APIFY_MODE=apify` in `backend/app/seller/job.py`; map results to `Flat` and verify count, price, district and URLs.
- [x] **I02** Save a real scrape as an offline fallback and label cached delivery clearly; retain the existing sample-data label. Depends on **I01**.
- [x] **I03** Run Max using `LLM_MODE=codex` with ChatGPT subscription sign-in; verify cap 10, budget 20 and approval above 8 remain enforced, with labelled scripted fallback on CLI/usage failures. Live checker/Act 1 pass; cancellation, bounded output, strict moves and seller-response identity have regression coverage.
- [x] **I04** Subscription Viktor implemented with `SELLER_LLM_MODE=codex`, independent floor/agreement checks, per-deal retry protection and labelled scripted fallback. Live checker and full two-agent Act 1 pass: 3 Max + 4 Viktor Codex turns, 20 cached real flats and 7 live voice clips in 42.2s, no fallback. Default remains scripted for the existing rehearsal; Act 2 always stays scripted.
- [x] **I05** Configure ElevenLabs voice IDs (`VOICE_MAX`, `VOICE_VIKTOR`) in `.env` and verify live `TTS_MODE=elevenlabs` output for both speakers.
- [x] **I06** Queue audio playback in negotiation order in the dashboard; keep text usable when audio fails. Actual Edge playback verifies replay/reset IDs, Stop/Mute, missing clips, stalled-clip recovery and sequential real speech. TTS response size, timeout and partial-file cleanup are covered.

## Integration and reliability

- [x] **R01** All four acts plus approval/decline work end to end locally. Verified rehearsal profile: subscription Max, scripted Viktor, **CACHED APIFY**, ElevenLabs with text fallback and **SIMULATED** money. Live Preprod remains a separate gate; Act 4 always stays SIMULATED.
- [x] **R02** Three consecutive runs of each act passed with subscription Max, scripted Viktor, cached real Apify, ElevenLabs and SIMULATED payments. Approval/decline also passed: 14 outcomes, 35 Codex turns, 100 speech clips, zero model/voice fallbacks. Three actual buyer crashes each recovered with one payment; seller stayed running. Reproduce with `backend/scripts/rehearse.py`; changing to subscription Viktor or Preprod requires a new rehearsal.
- [x] **R03** Two independent actual buyer-crash rehearsals (runner audit and endurance run) each recovered with one payment per deal while the seller stayed running. Two additional approval/restart checks preserved consent. All money was **SIMULATED**; repeat on Preprod only if **M04** passes.
- [x] **R04** Apify/TTS timeout and failure tests pass; real-cache, scripted-agent and text fallbacks survive repeated HTTP runs. Corrupt cache triggers refund instead of fabricated delivery. Stalled/missing audio clips do not block the queue.
- [x] **R05** Recording layout accepted at 1920×1080 in Edge: 16 screenshots, no horizontal overflow or page errors; negotiation, red blocked guard, release/refund, recovery, approval/decline and SIMULATED/STAGED/data labels are readable. Fixed Act 3's STAGED label to persist through restart/replay. Evidence: `backend/data/r-rehearsal-29b87432/`. This is layout acceptance; footage/export remain V02–V04.

## Video and release

- [x] **V01** Four-act [script and evidence storyboard](../../video/script.md) prepared for a 1:55 edit, including wallet guard, actual buyer crash recovery and honest limitations. Dashboard layout passed R05; actual video duration remains to be measured in V02.
- [x] **V05** README run steps, architecture, limitations, `.env.example` and handoff are current. Fresh source checkout without `.env`, caches or installed dependencies starts with `npm start` and completes a SIMULATED Act 1. Recheck documentation if the final payment/video profile changes.
- [x] **V06** [Repository/history audit](../../video/release-audit.md) covers all 48 reachable commits, 476 file blobs and the working source snapshot. Gitleaks findings reviewed as the documented Apify run ID; configured-secret check found no matches. GitHub public visibility and unauthenticated HTTP 200 confirmed. Rerun for the final revision and review footage before upload; keep credentials in ignored `.env` files only.

## Verified profile and limits

- R02/R05: subscription Max, scripted Viktor, cached real Apify, ElevenLabs and SIMULATED payments; three runs per act plus approval/decline, 35 Codex turns and 100 clips without fallback. Evidence: `backend/data/r-rehearsal-29b87432/`.
- I01–I06: all complete. Optional subscription Viktor passed a two-agent Act 1 in 42.2s with 20 cached real listings and seven live clips. Evidence: `backend/data/i-complete-97ac1034/`. Selecting this profile for recording requires a full rehearsal.
- Model access is subscription-only through local ChatGPT-authenticated Codex CLI; no OpenAI API token is expected. Act 2 remains scripted and labelled STAGED.
- Apify run `ZNboU2b0EHUJgFaEQ` supplies the genuine 20-listing cache; `scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ` recovers it without another paid run (run from `backend/`).
- Voice IDs are configured locally; `scripts/voice_check.py --synthesize` checks both voices and `scripts/llm_check.py --agent both` rejects fallback as live success.
- V01 is a script/storyboard, R05 is layout acceptance and V06 is a repository snapshot audit. None substitutes for recorded footage, a measured two-minute rehearsal or final export review.
