# The Haggle — build checklist

**2026-10-08 → 10-09 · Prague time · Target submission 07:00 · Hard deadline 07:14**

Tasks are unassigned so the team can split them later. Use the IDs when claiming work;
record active work in `memory/status/`. Check a task only after its acceptance condition
is met. The baseline below describes existing code, not proof that live integrations work.

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
- [x] **B02** Four acts verified in SIMULATED mode; automated coverage includes approval and crash recovery. Last recorded suite: 58 passing tests.
- [x] **B03** Masumi adapter and seller payment flow implemented and tested against a fake node; readiness checker supports `--node-only`.
- [x] **B04** OpenAI Agents SDK mode for Max implemented with scripted fallback; live API still unverified.
- [x] **B05** Dashboard stub consumes SSE, starts acts 1/2/4, displays balances and supports approval/decline. Production build verified.

## Startup and dashboard — by 23:30

- [ ] **D01** From `backend/`, sync dependencies and run Act 1 on every laptop: `uv sync`, `scripts/up.py --reset`, then `scripts/act.py honest`. Reset only a disposable simulated ledger.
- [ ] **D02** Replace the dashboard stub with two avatars, readable chat bubbles, balances and a clear event timeline.
- [ ] **D03** Show persistent **SIMULATED** and **STAGED** labels where applicable, sample/cached data provenance, a red **BLOCKED** banner and clear approval/decline controls.
- [ ] **D04** Verify dashboard act selection and complete acts 1, 2 and 4 from the UI; confirm each reaches its expected terminal state.
- [ ] **D05** Show Preprod transaction links and scheduled release time from SSE; do not present a scheduled release as settled funds. Depends on **M04** for live verification.

## Masumi payments — node by 23:30, live escrow by 01:00

- [ ] **M01** Bring up the hosted Railway/Blockfrost Preprod node or obtain a mentor-hosted node; pass `uv run python scripts/masumi_check.py --node-only`.
- [ ] **M02** Fund purchasing and selling wallets; register **Viktor only** with **Dynamic** pricing; confirm registration and balances in the admin UI. Depends on **M01**.
- [ ] **M03** Set local seller identifiers and pass the full `scripts/masumi_check.py`. This checks configuration, not live escrow. Depends on **M02**.
- [ ] **M04** Run Act 1 with `PAYMENTS_MODE=masumi` and a separate `LEDGER_PATH`; inspect the actual Preprod transaction and scheduled release. Depends on **M03**.
- [ ] **M05** Run staged Act 3 on the real setup: crash after lock, restart only the buyer, confirm `already_paid` and exactly one purchase. Depends on **M04**.

**Payment boundary:** Act 4 refund stays **SIMULATED**, even if acts 1 and 3 use Preprod.
Use separate real/simulated ledgers and restart services between modes after deals finish.
Never reset a ledger with unfinished payments or restart the seller mid-deal.

## Data, agents and voice — by 01:00

- [ ] **I01** Select an Apify actor for Praha 7 rentals and implement `APIFY_MODE=apify` in `backend/app/seller/job.py`; map results to `Flat` and verify count, price, district and URLs.
- [ ] **I02** Save a real scrape as an offline fallback and label cached delivery clearly; retain the existing sample-data label. Depends on **I01**.
- [ ] **I03** With OpenAI access, run Max using `LLM_MODE=openai`; verify the guard still enforces cap 10, budget 20 and approval above 8, including scripted fallback on API failure.
- [ ] **I04** Optional after the core flow works: add Viktor's LLM persona if OpenAI access is available. Viktor currently remains scripted.
- [ ] **I05** Configure ElevenLabs voice IDs (`VOICE_MAX`, `VOICE_VIKTOR`) in `.env` and verify live `TTS_MODE=elevenlabs` output for both speakers.
- [ ] **I06** Queue audio playback in negotiation order in the dashboard; keep text usable when audio fails. Depends on **I05**.

## Integration and reliability — 01:00–02:30

- [ ] **R01** Pass the 01:00 gate: all four acts plus approval/decline end to end; record which live integrations and fallbacks will appear in the video. Set `SELLER_FLOOR=9` to exercise approval.
- [ ] **R02** Run each act three consecutive times in the chosen demo configuration; fix any failure and repeat the affected act.
- [ ] **R03** Restart the buyer twice around the crash scenario and confirm one payment per deal; keep the seller running. Verify on Preprod if **M04** passed, otherwise label SIMULATED.
- [ ] **R04** Exercise Apify and TTS timeouts/failures; confirm the selected labelled data fallback or text fallback keeps the demo usable.
- [ ] **R05** Check the dashboard at 1080p: negotiation, guard decision, escrow outcome, approval controls and honesty labels must be readable in the recording.

## Video and release — 02:30–06:30

- [ ] **V01** Write a four-act script and storyboard, at most 2 minutes; include the wallet guard, crash recovery and honest limitations.
- [ ] **V02** Record backup footage of each working act, then complete the timed rehearsal by **03:30**. Depends on **R02**.
- [ ] **V03** After the **04:00 feature freeze**, record the demo with visible SIMULATED/STAGED labels; fix bugs between takes.
- [ ] **V04** Edit, add voiceover/captions and export the final video by **06:30**.
- [ ] **V05** Finalize README run steps, architecture and actual limitations; complete `.env.example`, update `memory/HANDOFF.md`, and verify startup from a fresh clone.
- [ ] **V06** Scan the repository and git history for secrets, then make the repository public by **06:30**. Keep credentials in ignored `.env` files only.

## Submission — 06:30–07:14

- [ ] **S01** Submit the form with the final video and repository links from **06:30**. Depends on **V04–V06**.
- [ ] **S02** By **06:50**, open every submitted link in incognito: repository accessible, video plays.
- [ ] **S03** Confirm submission by **07:00**, leaving the buffer before **07:14**.
