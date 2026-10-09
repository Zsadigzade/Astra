# The Haggle — active work

**2026-10-08 → 10-09 — Prague time — Target submission 07:00 — Hard deadline 07:14**

## HQ correction and recorded release — checked 05:05

The signed-in HQ overrides the old public website: **video ≤90 seconds**, **Unlisted
YouTube required**, **60-second stage pitch**, presentations **09:30**. Target submission
remains 07:00; the form closes 07:14. The 04:17 organizer announcement confirms these limits.
Replace every older two-minute/120-second video target below with **90 seconds**.

- P01: recorded application revision `1d9173c` (the approval prompt fix is committed),
  STRICT_LIVE codex/codex/apify/elevenlabs/SIMULATED. [Evidence](video/evidence.json).
- Capture/rehearsal: `backend/data/r-rehearsal-4f36a7e8/report.json`, **passed: true**;
  all four acts plus approve/decline, 18 Max + 24 Viktor live turns, 49 served speech clips,
  zero provider fallbacks. One crash-interrupted clip is separately unavailable.
- Tests: 579 backend, 63 frontend, production build. The six captured scenarios used the
  tested prompt fix. No new three-repeat acceptance is claimed.
- V03/V04: real footage and an approximately **89-second** narrated/captioned export are
  prepared at `backend/data/video/the-haggle-final.mp4`; final media checks and audit are
  recorded in [production](video/production.md) and [release audit](video/release-audit.md).
- The signed-in topic requires an executed transaction and allows a paid API. Apify reports
  actual billed usage (Act 1 USD 0.110573); this is separate from simulated agent escrow.
  Do not claim live Masumi, a real payment to Viktor, or a refund of provider charges.
- HQ project draft is saved. User will upload the MP4 as Unlisted on YouTube and supply
  the link. Submission and signed-out link acceptance remain pending until that happens.
- The [operator runbook, take index](video/production.md) and [60-second pitch](video/script.md)
  supersede older cached/scripted narration. Enable Play voices **after** starting each deal.

## SAFE PATH TO 07:00 (written 04:35) — subject to the HQ correction above

**05:20 update:** the user has assigned UI/UX work to their friend, expected around 05:50.
Presentation work continues separately. Preserve the accepted recording and source evidence;
do not restart the friend's services or reset their ledger. Inspect the completed UI diff,
run affected checks, and review labels/controls before accepting that revision. The stage
presenter is not yet selected; prepare materials any teammate can use.

No new product scope: no cars, request-parser widening, live Masumi (M02–M05/D05),
O01/O02 or D01 on other laptops. Only the recording laptop matters now.

**Recording profile (P01):** recorded application revision `1d9173c` (approval prompt fix committed), `STRICT_LIVE=1`: Codex Max + Codex Viktor, live
Apify, ElevenLabs, **SIMULATED** payments. Max's opening question is a fixed template labelled
scripted; every other line is live.

| By | Task | Owner | Done when |
|---|---|---|---|
| Done 04:53 | P01 live rehearsal at `1d9173c`, tests and production build | completed | all six captured cases pass |
| Now–05:50 | P02 remaining operator controls in an isolated session; prepare pitch cues and offline materials | presentation | controls evidence, handoff ready; human pitch timing pending |
| Done | V02/V03 six usable takes and edited export | completed | raw master, original speech, takes and final MP4 retained |
| Around 05:50 | Inspect friend's UI handoff; affected tests/build and browser review | presentation + UI owner | changed revision explicitly accepted or kept separate from recorded release |
| 06:15 | V04 full human listen-through of the 89.021333-second export | uploader | legible, audible, at most 90 seconds; preserve accepted fallback if recapture is risky |
| 06:25 | F01/F02 final revision, claims, public access and secret scan | presentation | baseline audit already complete; changed UI revision checked separately |
| Done | F03 evidence index and local backup | completed | revision, takes, deal IDs, profile and source bundle retained |
| 06:45 | S01 submit form (video + repo links) | submitter | confirmation received |
| 06:50 | S02 open both links in incognito | submitter | repo public, video plays |
| 07:00 | S03 record confirmation | submitter | done; buffer to 07:14 |

**Fallback gates — decide at the time, do not debate:**
- If a new UI revision or take fails, retain the already accepted live recording. No new
  provider calls are needed for pitch practice or editing. Never fake a successful take.
- **06:15**, replacement edit not exported: use the existing verified 89-second MP4.
- **06:45**, upload delayed: continue uploading the verified MP4, or retain an already
  valid Unlisted link. HQ requires YouTube; repository-only submission and other hosting
  are not established fallbacks. Never enter a placeholder video link.

**P02 operator runbook (recording laptop):**
1. `npm start` from repo root (`.env` holds tokens; dashboard gets the token automatically).
   Health: buyer shows `codex/codex/elevenlabs`, seller shows `apify_mode: apify`.
2. Dashboard http://localhost:5173 at 1920×1080, browser zoom 100%, notifications off, no
   private tabs or `.env` on screen.
3. Act 1: Mode **Normal**, default request, **Run request**. Live acts took 50–110 s in the 04:52 rehearsal; cut waits in the edit.
4. Act 2: Mode **Con**. Expect Viktor's "manager approved 25", Max accepts, **Payment blocked**.
5. Act 3: **Recovery** is terminal-only. Stop `npm start` (no deal running), then from `backend/`
   run `uv run python scripts/up.py --crash`, and `npm run web` from the root in a second terminal.
   Run a **Normal** request: buyer dies after the escrow lock, restarts once, shows `already_paid`.
   Never restart the seller mid-deal. Afterwards stop both and go back to `npm start`.
6. Act 4: Mode **Refund**. Expect 3 sabotaged listings, verification fails, refund.
7. Approval: stop services, then in PowerShell from `backend/`: `$env:SELLER_FLOOR=9; uv run python scripts/up.py`
   plus `npm run web`. Run a **Normal** request; the deal settles at 9 and waits; click **Approve**
   within 5 min. Remove `SELLER_FLOOR` and restart afterwards.
8. Audio: **Run request, then Play voices**; a new deal resets the queue. Stop/Mute between takes.
9. Pause stops new tasks; existing deals finish. Reset only a stopped, completed simulated
   ledger. Never reset unfinished/real payments. Full instructions: [production](video/production.md).

**Updated 2026-10-09 01:50.** [31 completed items are archived](memory/archive/COMPLETED.md),
including all **I01–I14** and the earlier **R01–R05** acceptance. the tables below retain the original task IDs. The release update above is authoritative;
conditional live-payment work, other laptops and optional improvements are deferred.
Use IDs to claim work in `memory/status/`; assignments remain open.
New I-path acceptance: 527 backend tests, 41 frontend tests/build, synthetic Edge controls/layout,
and one live run of each of the four acts with SIMULATED money. This is not a new three-runs-per-act
R02 acceptance or a timed video rehearsal. Evidence: [system checks](memory/SYSTEM_CHECK.md).

**Next:** finish P02 operator controls and presenter materials, human V04 sound check,
then F02 review of the friend's finished UI. User supplies the Unlisted URL for S01–S03.
Live-payment and other-laptop work are deferred. Use the [video package](video/README.md)
for the current script, final captions and capture evidence.

**Historical baseline (superseded by the recorded live release above):** all four acts, approval/decline, actual buyer crash recovery and
1920×1080 layout pass with subscription Max, scripted Viktor (`SELLER_LLM_MODE=mock`),
cached real Apify, ElevenLabs and **SIMULATED** payments. Subscription Viktor also passed
live Act 1; using it for recording needs O01. Model access stays subscription-only via
local ChatGPT-authenticated Codex CLI, with labelled scripted fallback; no API token is expected.
That rehearsal predates the new I-path changes. The latest tested working-tree snapshot
passed **523 backend tests**; it is not a new live-profile rehearsal or final-release audit.

## Remaining gates

| Time | Acceptance / action |
|---|---|
| **01:00** | If live Preprod escrow is not proven, use the validated SIMULATED profile for the video. Preserve visible money/data/fallback labels. |
| **Completed** | 89.021333-second final video fits the HQ 90-second limit. |
| **Around 05:50** | Friend's UI handoff; accept only after affected checks. Preserve recorded baseline. |
| **06:30** | Final video exported, repository public and final-revision audit complete. |
| **06:50** | Both submitted links verified in incognito. |
| **07:00** | Submission confirmed; retain the buffer before **07:14**. |

## Recording setup and operator readiness

- [x] **P01 · NEW** Record the chosen demo profile and code revision in [video/production.md](video/production.md), including model modes, data source, voice and payment mode. The baseline above already passed archived R02/R05; a changed model/payment profile needs its relevant rehearsal before capture. Select SIMULATED at the 01:00 gate if live proof is still missing.
- [ ] **D01** Run Act 1 on every laptop. Root `npm start` installs dependencies and starts all three services; a fresh source checkout passed locally without keys. Each teammate still needs to confirm startup; subscription mode requires their own `codex login`. Reset only a disposable simulated ledger. Record each laptop's result and profile.
- [ ] **P02 · NEW** Software sequence complete: recorded launch/acts/approval/crash, plus isolated Pause/Resume, real saved-audio Play/Stop/Mute/replay/speed and safe reset. Evidence: `backend/data/r-rehearsal-e56af9a2/report.json`; no new provider calls. [Runbook and stage materials](video/production.md) are ready. Remaining human steps: select speaker, time one pitch and confirm audible playback on the presentation laptop. Preserve the seller during funded recovery.

## Live Preprod payments — conditional and currently blocked

This section is separate from the SIMULATED video path. Archived **M01** passed hosted
health, authentication and Preprod source checks; it does not prove funding or escrow.

- [ ] **M02** Fund purchasing and selling wallets; register **Viktor only** with **Dynamic** pricing; confirm registration and balances in the admin UI. Depends on archived **M01**. **Last reported blocker:** the Preprod transaction has 8 confirmations and its stake address matches the Selling Wallet, but Masumi still displays a zero balance; registration is pending. Keep payments **SIMULATED** until the node reflects funding and Viktor is registered.
- [ ] **M03** Set local seller identifiers and pass the full `scripts/masumi_check.py` from `backend/`. Last readiness check lacked `MASUMI_AGENT_ID` and a valid `SELLER_VKEY`. This checks configuration, not live escrow. Depends on **M02**; credentials stay local.
- [ ] **M04** Run Act 1 with `PAYMENTS_MODE=masumi` and a separate `LEDGER_PATH`; inspect and record the actual Preprod transaction and scheduled release. Depends on **M03**.
- [ ] **D05** Verify actual Preprod transaction links and scheduled release time in the dashboard from SSE. UI/accounting already pass synthetic-event tests; do not present scheduled release as settled funds. Depends on **M04**.
- [ ] **M05** Run staged Act 3 on the real setup: crash after lock, restart only the buyer, confirm `already_paid` and exactly one purchase. Depends on **M04**. If selected for video, repeat the full rehearsal with this payment profile.

**Payment boundary:** Act 4 refund always stays **SIMULATED**. Keep real/simulated ledgers
separate and restart services between modes only after deals finish. Never reset a ledger
with unfinished payments or restart the seller mid-deal. Live release is scheduled, not settled.

## Video capture, edit and export

- [x] **V02** Six scenario takes and a 585.12-second raw master are retained. The final edited recording measures **89.021333 seconds**, within HQ's 90-second limit. Durations and take paths: [production](video/production.md).
- [x] **V03** After the **04:00 feature freeze**, record the final demo with visible SIMULATED/STAGED and data/fallback labels; fix bugs between takes. Archived **R05** passed layout acceptance. Follow the capture/evidence requirements and retain a usable take for each act.
- [ ] **V04** Export, voiceover and [final captions](video/narration-final.srt) are complete. Automated full playback and visual chapter checks pass. A human must listen through the final MP4 once before upload. Details: [production](video/production.md).

## Final release and evidence — new

- [x] **F01 · NEW** Record the final code revision and reconcile README, `.env.example`, handoff and video narration with the selected profile and honest limitations. Archived **V05** covers the earlier baseline. If code/configuration changed after rehearsal, run the affected checks and record results before declaring the release ready.
- [ ] **F02 · NEW** Recorded/published baseline `962e91b` has passed history/object/source/media secret review and signed-out public access: 70 commits, 778 blobs, 210 source files; run-ID scanner findings reviewed as nonsecrets. The friend's UI handoff needs affected checks and a final revision/public-access update before acceptance. Preserve the existing video/source audit in [release-audit](video/release-audit.md).
- [x] **F03 · NEW** Create a concise final evidence index in [video/production.md](video/production.md): code revision/profile, chosen takes/export location, measured duration, representative deal IDs, data provenance and reproduction commands. Confirm raw footage and nonsecret evidence have a recoverable copy; link public transaction evidence only if live verification passed. Keep `.env`, authentication stores and credentials out of the package. Depends on **V04/F01**.

## Submission — 06:30–07:14

- [ ] **S01** Submit the form with the final video and repository links from **06:30**. Depends on **V04/F01–F03**; archived **V05/V06** remain baseline evidence, not final-release sign-off.
- [ ] **S02** By **06:50**, open every submitted link in incognito: repository accessible and video plays. Fix permissions or links and recheck if necessary.
- [ ] **S03** Confirm submission by **07:00**, leaving the buffer before **07:14**. Record the confirmation and exact submitted links.

## Completed data, agent and voice improvements

I07–I14 are implemented and [archived with acceptance notes](memory/archive/COMPLETED.md):
cache freshness and separate request caches, validation reports, reusable speech, immediate
transcripts, replay/speed controls, bounded Codex concurrency and unified readiness.
I13/I14 were completed by the parallel terminal sessions. The affected four-act live run passed;
recording, repeated final-profile acceptance if needed, and release/submission gates remain above.

## Optional improvements to existing I work — after submission

These are follow-ups, not unfinished I01–I14 acceptance. Defer them until submission;
the selected subscription Viktor profile has one captured run per case. O01's three-repeat
acceptance remains optional and is not claimed by this submission.

- [ ] **O01 · NEW** Repeat the full three-runs-per-act plus approval/decline rehearsal with `SELLER_LLM_MODE=codex`. Record per-agent live/fallback counts, voice results, payment recovery and timings; keep Act 2 scripted/STAGED. I04's live two-agent Act 1 already passed, but it does not establish full-profile R02 acceptance.
- [ ] **O02 · NEW** Measure existing data/agent/voice latency across repeat Act 1 runs: negotiation, cache verification, first playable speech and total completion. Record a baseline, then fix the largest confirmed bottleneck within those existing paths and compare results. Preserve ordering, provenance and honest fallback labels; reuse the saved Apify run instead of starting paid scrapes just for timing.
