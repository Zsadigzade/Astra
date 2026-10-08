# The Haggle — build checklist

**2026-10-08 → 10-09 · Prague time · Target submission 07:00 · Hard deadline 07:14**

**Updated 2026-10-09 00:54 · 23 of 35 checklist items complete.** All **I01–I06** are complete.
The core SIMULATED demo, three-runs-per-act rehearsal and 1080p dashboard checks pass.
Remaining work is cross-laptop acceptance, live-payment gates, timed video rehearsal,
recording/edit/export and submission.

Use the IDs when claiming work and record ownership in `memory/status/`. Checked items have
recorded evidence in [memory/SYSTEM_CHECK.md](memory/SYSTEM_CHECK.md); local success does not
complete every-laptop or live-Preprod acceptance.

**Next priorities:** D01 (each laptop), then V02–V04 (timed rehearsal, recording and edit).
R02/R05 passed for the scripted-Viktor profile; V01's script is ready in
[video/](video/README.md). M02–M05 remain the separate live-payment path.

**Validated recording profile:** subscription Max, scripted Viktor (`SELLER_LLM_MODE=mock`),
cached real Apify listings, ElevenLabs and SIMULATED payments. Subscription Viktor is also
implemented and live-verified; switching the recording to it requires another R02 rehearsal.

## Gates

| Time | Pass condition | Fallback / action |
|---|---|---|
| **22:15** | Act 1 runs SIMULATED, text only, on every laptop | Fix the shared startup blocker before integration |
| **23:30** | Acts 1, 2 and 4 run from dashboard buttons; Masumi node is available | No live node → commit to SIMULATED money for the video |
| **01:00** | All four acts and the approval path run end to end | No Preprod escrow → SIMULATED video; cut broken voice first; flaky Apify → labelled saved real JSON |
| **03:30** | Full demo rehearsal finishes within 2 minutes | Trim the script before recording |
| **04:00** | Feature freeze; recording starts | Bug fixes only |
| **06:30** | Video exported; repository public | Check submission links immediately |
| **07:00** | Submission sent and links checked in incognito | Keep the 14-minute buffer; **07:14 is final** |

## Existing baseline

- [x] **B01** Buyer and seller HTTP services, negotiation, wallet guard and verifier exist.
- [x] **B02** Four acts verified in SIMULATED mode; automated coverage includes approval, crash recovery and adversarial deliveries. I-completion suite: 390 tests on Python 3.11/3.13; shared workspace also passes two pending R-path regressions (392 total).
- [x] **B03** Masumi adapter and seller payment flow implemented and tested against a fake node; readiness checker supports `--node-only`.
- [x] **B04** Scripted negotiation works; subscription Codex replaces the API-key runtime, with explicit fallback labels and independent wallet guard.
- [x] **B05** Full dashboard consumes SSE, starts acts 1/2/4, displays balances, guard decisions and approvals; pause/limits, themes and ordered audio work. 33 frontend tests and production build pass.

## Startup and dashboard — by 23:30

- [ ] **D01** Run Act 1 on every laptop. Root `npm start` installs dependencies and starts all three services; a fresh source checkout passed locally without keys. Each teammate still needs to confirm startup; subscription mode also requires their own `codex login`. Reset only a disposable simulated ledger.
- [x] **D02** Replace the dashboard stub with two avatars, readable chat bubbles, balances and a clear event timeline. Implemented and browser-tested.
- [x] **D03** Show persistent **SIMULATED** and **STAGED** labels where applicable, sample/cached data provenance, a red blocked guard state and clear approval/decline controls. Verified in Edge.
- [x] **D04** Verify dashboard act selection and complete acts 1, 2 and 4 from the UI. Honest release, con blocked and junk refund pass, as do approval/decline and offline/reconnect.
- [ ] **D05** Show Preprod transaction links and scheduled release time from SSE; do not present a scheduled release as settled funds. UI and accounting are implemented/tested with synthetic events; actual transaction/link verification still depends on **M04**.

## Masumi payments — node by 23:30, live escrow by 01:00

- [x] **M01** Bring up the hosted Railway/Blockfrost Preprod node and pass `uv run python scripts/masumi_check.py --node-only`. Hosted health, authentication and Preprod payment-source checks passed; the earlier 401 is resolved.
- [ ] **M02** Fund purchasing and selling wallets; register **Viktor only** with **Dynamic** pricing; confirm registration and balances in the admin UI. Depends on **M01**. **Blocked:** the Preprod transaction has 8 confirmations and its stake address matches the Selling Wallet, but Masumi still displays a zero balance; registration remains pending. Keep payments **SIMULATED** until the node reflects funding and Viktor is registered.
- [ ] **M03** Set local seller identifiers and pass the full `scripts/masumi_check.py`. Local `MASUMI_AGENT_ID` and a valid `SELLER_VKEY` remain missing. This checks configuration, not live escrow. Depends on **M02**.
- [ ] **M04** Run Act 1 with `PAYMENTS_MODE=masumi` and a separate `LEDGER_PATH`; inspect the actual Preprod transaction and scheduled release. Depends on **M03**.
- [ ] **M05** Run staged Act 3 on the real setup: crash after lock, restart only the buyer, confirm `already_paid` and exactly one purchase. Depends on **M04**.

**Payment boundary:** Act 4 refund stays **SIMULATED**, even if acts 1 and 3 use Preprod.
Use separate real/simulated ledgers and restart services between modes after deals finish.
Never reset a ledger with unfinished payments or restart the seller mid-deal.

## Data, agents and voice — by 01:00

**6/6 complete.** A fresh two-agent Act 1 used three Max and four Viktor subscription Codex turns,
20 cached real listings and seven live speech clips, with no fallback and SIMULATED release in 42.2s.
Model access is permanently subscription-only: ChatGPT-authenticated Codex CLI with labelled
scripted fallback; no API token is expected.

- [x] **I01** Select an Apify actor for Praha 7 rentals and implement `APIFY_MODE=apify` in `backend/app/seller/job.py`; map results to `Flat` and verify count, price, district and URLs.
- [x] **I02** Save a real scrape as an offline fallback and label cached delivery clearly; retain the existing sample-data label. Depends on **I01**.
- [x] **I03** Run Max using `LLM_MODE=codex` with ChatGPT subscription sign-in; verify cap 10, budget 20 and approval above 8 remain enforced, with labelled scripted fallback on CLI/usage failures. Live checker/Act 1 pass; cancellation, bounded output, strict moves and seller-response identity have regression coverage.
- [x] **I04** Subscription Viktor implemented with `SELLER_LLM_MODE=codex`, independent floor/agreement checks, per-deal retry protection and labelled scripted fallback. Live checker and full two-agent Act 1 pass: 3 Max + 4 Viktor Codex turns, 20 cached real flats and 7 live voice clips in 42.2s, no fallback. Default remains scripted for the existing rehearsal; Act 2 always stays scripted.
- [x] **I05** Configure ElevenLabs voice IDs (`VOICE_MAX`, `VOICE_VIKTOR`) in `.env` and verify live `TTS_MODE=elevenlabs` output for both speakers.
- [x] **I06** Queue audio playback in negotiation order in the dashboard; keep text usable when audio fails. Actual Edge playback verifies replay/reset IDs, Stop/Mute, missing clips, stalled-clip recovery and sequential real speech. TTS response size, timeout and partial-file cleanup are covered.

Recorded Apify run: `ZNboU2b0EHUJgFaEQ`; recover its 20 listings with
`scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ` (no new run).
Brian/Callum voices are configured locally; `scripts/voice_check.py --synthesize` passed both.
`scripts/llm_check.py --agent both` checks both live agents and rejects fallback as live success.
Model setup uses `codex login` on each laptop; credentials stay in Codex's store. No waiting for API keys.
Act 2 intentionally uses scripted Max and Viktor in every mode, with STAGED/scripted labels.

## Integration and reliability — 01:00–02:30

- [x] **R01** All four acts plus approval/decline work end to end locally. Verified rehearsal profile: subscription Max, scripted Viktor, **CACHED APIFY**, ElevenLabs with text fallback and **SIMULATED** money. Live Preprod remains a separate gate; Act 4 always stays SIMULATED.
- [x] **R02** Three consecutive runs of each act passed with subscription Max, scripted Viktor, cached real Apify, ElevenLabs and SIMULATED payments. Approval/decline also passed: 14 outcomes, 35 Codex turns, 100 speech clips, zero model/voice fallbacks. Three actual buyer crashes each recovered with one payment; seller stayed running. Reproduce with `backend/scripts/rehearse.py`; changing to subscription Viktor or Preprod requires a new rehearsal.
- [x] **R03** Two independent actual buyer-crash rehearsals (runner audit and endurance run) each recovered with one payment per deal while the seller stayed running. Two additional approval/restart checks preserved consent. All money was **SIMULATED**; repeat on Preprod only if **M04** passes.
- [x] **R04** Apify/TTS timeout and failure tests pass; real-cache, scripted-agent and text fallbacks survive repeated HTTP runs. Corrupt cache triggers refund instead of fabricated delivery. Stalled/missing audio clips do not block the queue.
- [x] **R05** Recording layout accepted at 1920×1080 in Edge: 16 screenshots, no horizontal overflow or page errors; negotiation, red blocked guard, release/refund, recovery, approval/decline and SIMULATED/STAGED/data labels are readable. Fixed Act 3's STAGED label to persist through restart/replay. Evidence: `backend/data/r-rehearsal-29b87432/`. This is layout acceptance; footage/export remain V02–V04.

## Video and release — 02:30–06:30

- [x] **V01** Four-act [script and evidence storyboard](video/script.md) prepared for a 1:55 edit, including wallet guard, actual buyer crash recovery and honest limitations. Dashboard layout passed R05; actual video duration remains to be measured in V02.
- [ ] **V02** Record backup footage of each working act, then complete the timed rehearsal by **03:30**. Depends on **R02**. [Capture requirements and take/rehearsal record](video/production.md) prepared; footage and measured rehearsal pending.
- [ ] **V03** After the **04:00 feature freeze**, record the demo with visible SIMULATED/STAGED labels; fix bugs between takes. Evidence/label requirements and R05 layout acceptance are ready; final footage is still pending.
- [ ] **V04** Edit, add voiceover/captions and export the final video by **06:30**. [Draft captions](video/narration-draft.srt) and export checks prepared; retiming, actual voiceover, edit and export pending.
- [x] **V05** README run steps, architecture, limitations, `.env.example` and handoff are current. Fresh source checkout without `.env`, caches or installed dependencies starts with `npm start` and completes a SIMULATED Act 1. Recheck documentation if the final payment/video profile changes.
- [x] **V06** [Repository/history audit](video/release-audit.md) covers all 48 reachable commits, 476 file blobs and the working source snapshot. Gitleaks findings reviewed as the documented Apify run ID; configured-secret check found no matches. GitHub public visibility and unauthenticated HTTP 200 confirmed. Rerun for the final revision and review footage before upload; keep credentials in ignored `.env` files only.

## Submission — 06:30–07:14

- [ ] **S01** Submit the form with the final video and repository links from **06:30**. Depends on **V04–V06**.
- [ ] **S02** By **06:50**, open every submitted link in incognito: repository accessible, video plays.
- [ ] **S03** Confirm submission by **07:00**, leaving the buffer before **07:14**.
