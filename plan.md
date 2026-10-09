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

**Code is frozen.** Bug fixes only, and only for something that breaks a recorded act. No new
features: no cars or other products, no request-parser widening, no live Masumi (M02–M05/D05),
no O01/O02, no D01 on other laptops. Only the recording laptop matters now.

**Recording profile (P01):** recorded application revision `1d9173c` (approval prompt fix committed), `STRICT_LIVE=1`: Codex Max + Codex Viktor, live
Apify, ElevenLabs, **SIMULATED** payments. Max's opening question is a fixed template labelled
scripted; every other line is live.

| By | Task | Owner | Done when |
|---|---|---|---|
| ✅ 04:53 | Restart services on `8a95421`; backend/frontend tests + build; one live rehearsal run of every act + approve/decline | Claude | rehearsal `passed: true`, services healthy on live modes |
| 05:05 | P02 operator runbook (below) dry-run once on the recording laptop | recorder | each step done once without notes |
| 05:45 | V02/V03 record one good take per act (1, 2, 3, 4) + one approval take; retake failures immediately | recorder | 5 usable takes saved, paths logged in `video/production.md` |
| 06:15 | V04 edit to ≤120 s (cut scrape/model waits), voiceover, captions, export MP4 | editor | `ffprobe` ≤120 s, full watch with audio |
| 06:25 | F01/F02 final revision, README/handoff check, secret scan of repo **and** exported video frames | Claude + editor | `video/release-audit.md` updated |
| 06:30 | F03 evidence index in `video/production.md` | Claude | revision, takes, deal IDs, profile listed |
| 06:45 | S01 submit form (video + repo links) | submitter | confirmation received |
| 06:50 | S02 open both links in incognito | submitter | repo public, video plays |
| 07:00 | S03 record confirmation | submitter | done; buffer to 07:14 |

**Fallback gates — decide at the time, do not debate:**
- **05:30**, a live take keeps failing (Codex/Apify error on screen): set `STRICT_LIVE=0`
  (labelled fallbacks allowed), restart after deals finish, retake. If Apify itself is down:
  `APIFY_MODE=cached` (shows CACHED APIFY).
- **05:45**, an act still has no usable take: use that act's screenshot from
  `backend/data/r-rehearsal-*/` with voiceover. Never fake a take.
- **06:15**, edit not exported: export what exists (Acts 1 + 2 minimum) at ≤120 s.
- **06:45**, video upload stuck: submit with repo link, then retry upload; keep the 07:14 buffer.

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
8. Audio: Play voices on before each take; Stop/Mute between takes.

**Updated 2026-10-09 01:50.** [31 completed items are archived](memory/archive/COMPLETED.md),
including all **I01–I14** and the earlier **R01–R05** acceptance. the tables below retain the original task IDs. The release update above is authoritative;
conditional live-payment work, other laptops and optional improvements are deferred.
Use IDs to claim work in `memory/status/`; assignments remain open.
New I-path acceptance: 527 backend tests, 41 frontend tests/build, synthetic Edge controls/layout,
and one live run of each of the four acts with SIMULATED money. This is not a new three-runs-per-act
R02 acceptance or a timed video rehearsal. Evidence: [system checks](memory/SYSTEM_CHECK.md).

**Next:** agree the recording profile (P01), confirm laptop/operator readiness (D01/P02),
then capture and time the demo (V02). Continue M02–M05/D05 separately if live payments
become ready. Final evidence is in [memory/SYSTEM_CHECK.md](memory/SYSTEM_CHECK.md);
the [video package](video/README.md) contains the script, draft captions and capture instructions.

**Working baseline:** all four acts, approval/decline, actual buyer crash recovery and
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
| **03:30** | Measured full video rehearsal fits within 2 minutes; trim the script if needed. |
| **04:00** | Feature freeze and final recording; bug fixes only afterward. |
| **06:30** | Final video exported, repository public and final-revision audit complete. |
| **06:50** | Both submitted links verified in incognito. |
| **07:00** | Submission confirmed; retain the buffer before **07:14**. |

## Recording setup and operator readiness

- [x] **P01 · NEW** Record the chosen demo profile and code revision in [video/production.md](video/production.md), including model modes, data source, voice and payment mode. The baseline above already passed archived R02/R05; a changed model/payment profile needs its relevant rehearsal before capture. Select SIMULATED at the 01:00 gate if live proof is still missing.
- [ ] **D01** Run Act 1 on every laptop. Root `npm start` installs dependencies and starts all three services; a fresh source checkout passed locally without keys. Each teammate still needs to confirm startup; subscription mode requires their own `codex login`. Reset only a disposable simulated ledger. Record each laptop's result and profile.
- [ ] **P02 · NEW** Rehearse the operator sequence on the actual recording laptop and add a short runbook to [video/production.md](video/production.md): startup, act selection, pause/approval, one staged buyer restart, audio Play/Stop/Mute and safe reset. Confirm cache, local sign-in and voices for the selected profile, and record who operates capture. Preserve the seller process during funded recovery.

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

- [x] **V02** Record backup footage of each working act, then complete a measured rehearsal of at most 2 minutes by **03:30**. Archived **R02** passed for the baseline; complete **P01/P02** before capture. Log duration and take paths in [video/production.md](video/production.md). The 1:55 [script](video/script.md) is a target, not a measured recording.
- [x] **V03** After the **04:00 feature freeze**, record the final demo with visible SIMULATED/STAGED and data/fallback labels; fix bugs between takes. Archived **R05** passed layout acceptance. Follow the capture/evidence requirements and retain a usable take for each act.
- [ ] **V04** Edit, add voiceover, retime the [draft captions](video/narration-draft.srt) and export the final video by **06:30**. Check actual duration, legibility, audio and playback of the exported file against [video/production.md](video/production.md). Depends on **V03**.

## Final release and evidence — new

- [x] **F01 · NEW** Record the final code revision and reconcile README, `.env.example`, handoff and video narration with the selected profile and honest limitations. Archived **V05** covers the earlier baseline. If code/configuration changed after rehearsal, run the affected checks and record results before declaring the release ready.
- [ ] **F02 · NEW** Repeat the repository/history secret scan and unauthenticated public-access check at the final revision; review the actual exported video for exposed credentials or private windows before upload. Append final revision/results to [video/release-audit.md](video/release-audit.md). Archived **V06** covers an earlier 48-commit/476-blob snapshot. Depends on **F01/V04**.
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
if the team chooses subscription Viktor for this video, bring O01 forward before V02.

- [ ] **O01 · NEW** Repeat the full three-runs-per-act plus approval/decline rehearsal with `SELLER_LLM_MODE=codex`. Record per-agent live/fallback counts, voice results, payment recovery and timings; keep Act 2 scripted/STAGED. I04's live two-agent Act 1 already passed, but it does not establish full-profile R02 acceptance.
- [ ] **O02 · NEW** Measure existing data/agent/voice latency across repeat Act 1 runs: negotiation, cache verification, first playable speech and total completion. Record a baseline, then fix the largest confirmed bottleneck within those existing paths and compare results. Preserve ordering, provenance and honest fallback labels; reuse the saved Apify run instead of starting paid scrapes just for timing.
