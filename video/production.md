# The Haggle recording, operation and submission handoff

## Current release

HQ requires **at most 90 seconds**, an **unlisted YouTube link**, and a **60-second stage pitch**. The signed-in 04:17 organizer update supersedes the earlier two-minute instructions. Target submission: **07:00, 9 October 2026**; hard close **07:14**, Prague/Budapest time. HQ lists presentations at **09:30**.

- Recorded application revision: **`1d9173c7325482bc204bfc145376963d96bb6cdc`**. This is `8a95421` plus the approval-path prompt fix; source hashes and that patch were preserved with the capture.
- Profile: `STRICT_LIVE=1`, Max/Viktor `codex`, data `apify`, speech `elevenlabs`, payments `simulated`. Max's opening and guard notices are code-generated; model decisions and Viktor's dialogue are live.
- Guard cap 10, human approval above 8, task budget 20; rehearsal starting balances 100 / 0 / 0. Each run used a private SIMULATED ledger and private ports.
- Acceptance: **579 backend tests, 63 frontend tests, production build**, one recorded run of every act plus approve/decline. No three-repeat acceptance is claimed. All six runs pass; no browser page errors or provider fallbacks. 18 live Max decisions, 24 live Viktor turns, 49 served speech clips; one intentional crash-interrupted clip is explicitly unavailable.
- Public, nonsecret results: [evidence.json](evidence.json). Local full report: `backend/data/r-rehearsal-4f36a7e8/report.json`.

## Export and take index

Final upload file: **`backend/data/video/the-haggle-final.mp4`**. Captions are burned in; the matching sidecar is `backend/data/video/the-haggle-final.srt`. The edit is **89.021333 seconds**, 1920×1080, H.264/yuv420p, constant 30 fps, AAC stereo/48 kHz, normalized speech, fast-start MP4. Exact measured metadata, hash and full browser-playback results are recorded in the local `playback-review.json` and release audit.

The final con uses original recorded Viktor/Max audio. Other chapters use ElevenLabs narration. Waits and some dialogue are cut; event order within each deal is preserved. Editorial STAGED and SIMULATED ESCROW labels remain visible. Process and provider-charge overlays are derived from the actual report, not reenacted events.

Uncut silent screen master (585.12 s): `backend/data/r-rehearsal-4f36a7e8/raw/page@bf64962a426dbaeaecd63740a5da2214.webm`. Original speech MP3s are preserved in that run's `audio/` folder. The master does not contain a system-audio track. The final edit restores the chosen original con clips.

| Take | Deal | Outcome | Master range (seconds) |
| --- | --- | --- | --- |
| Act 1 | `05ec69ddd9bd49e484d2` | 20 LIVE APIFY records; release 7 | 5.541–105.167 |
| Act 2 | `6a61c18522264d2999da` | 25 blocked at cap 10; no lock | 105.168–171.837 |
| Act 3 | `21e473880c754b18add4` | Actual buyer exit/restart; one lock, one already_paid, one release | 171.845–288.153 |
| Act 4 | `2b1d3e01275f44a39eec` | Three sabotaged records; verification fails; refund 7 | 288.155–369.791 |
| Approve | `3028b46e27e746efb24b` | Approval at 9, then release | 376.515–484.150 |
| Decline | `42c50b8af72b4bc1afd8` | Explicit decline; no lock | 484.153–584.734 |

Final rehearsal balances: **77 buyer / 23 seller / 0 escrow**. Provider usage is separate: four successful Apify runs report USD 0.110573, 0.105917, 0.105221 and 0.105542 respectively. These are real billed API usage, not Masumi transfers or a real payment to Viktor. Simulated refunds do not reverse provider charges. Run IDs and charged event counts are in the evidence index; full read-only provider metadata stays with the local recording.

## Operator runbook: this laptop

The capture exercised this sequence through the actual dashboard and service runner. A human still needs to hear the final export before uploading and time their spoken pitch.

1. From the repository root, `npm start`. It loads the private `.env` and passes the buyer token to the local dashboard. Open `http://localhost:5173` at 1920×1080, 100% zoom. Keep notifications and private windows out of capture.
2. Health must show buyer `codex/codex/elevenlabs`, SIMULATED payments, guard 10/8; seller must show `apify_mode: apify`. The current laptop passed these checks, authenticated access, and dashboard HTTP 200. No-token buyer access correctly returns 401.
3. **Normal:** keep the default 20-flat request, click Run request, then **Play voices**. A new deal resets the audio queue, so enable playback after launch. Expect live negotiation, scrape, verification and release. Recorded end-to-end wall times were roughly 67–117 seconds per act; the submitted video shortens waits.
4. **Con:** select Con, run, then Play voices. Expect manager-approved 25, Max's acceptance, Payment blocked, cap 10, no funded escrow. The gullible role is deliberately STAGED.
5. **Recovery:** after every current deal finishes, stop the owning `npm start` session. In `backend/`, run `uv run python scripts/up.py --crash`; in a second terminal at the root, run `npm run web`. Launch a Normal request. Only the buyer exits and restarts; preserve the seller and the same ledger. Confirm already_paid and a single release. Afterwards stop both owned sessions and return to `npm start`.
6. **Refund:** select Refund, run and enable voices. A live scrape is sabotaged to three invalid records; verification fails and simulated escrow returns.
7. **Approval/decline:** after all deals finish, stop services. In the backend terminal set `$env:SELLER_FLOOR=9`, run `uv run python scripts/up.py`, and start `npm run web` from the root in a second terminal. Launch Normal; use the visible Approve or Decline control within five minutes. When done, stop these sessions, `Remove-Item Env:SELLER_FLOOR`, then return to `npm start`.
8. **Audio:** Stop between takes, Mute when narrating. Replay uses saved clips. The intentional buyer crash may leave one unavailable clip; its transcript and money recovery remain valid.
9. **Reset only if needed:** stop services after every payment finishes; `scripts/up.py --reset` archives only a completed SIMULATED ledger. Never reset unfinished/real/mixed payments. No destructive reset was needed for this capture. Do not restart the seller during a funded deal.

Read-only prerequisites: `cd backend; uv run --locked python scripts/readiness.py`.

Repeat acceptance only when a relevant change warrants another paid run:

```powershell
uv run --locked --with playwright python scripts/rehearse.py --browser --seller-mode codex --data-mode apify --repeats 1
```

One pass can start **four** paid scrapes (normal, recovery, junk and approved delivery), each requesting a $1.10 Actor charge cap. Three repeats can start ten. Codex and speech quota also apply. Use the already recorded evidence for presentation and editing.

## Submission handoff

### Presenter materials and remaining operator checks

Open [presenter.html](presenter.html) locally for the stage slide, 129-word speaking
draft and a start/pause/reset rehearsal timer. Stage view hides notes; Escape restores
them. The timer warns at 60 seconds. Offline exports are in `backend/data/presentation/`:
`stage-slide.pdf`, `stage-slide-1920x1080.png`, `pitch-cues.pdf` and `pitch-cues.png`.
Both PDFs have one page. Edge controls and 1920x1080 slide fit were verified; the
rendered slide and cues were visually inspected. The intended timings are cues,
not a measured human performance. Choose a speaker and rehearse once with sound.

P02's remaining software controls passed on private ports using a copy of the
completed recording ledger and original saved speech, with new model/voice/data calls
disabled: Pause rejects new tasks with HTTP 423; Resume restores launch; real browser
Audio elements play, stop, mute, unmute, replay and change speed. Balances stayed
77 / 23 / 0. Safe reset archived only the stopped copy, preserving identical bytes.
The source recording ledger and the friend's active services were untouched; all
owned check services stopped. Evidence: `backend/data/r-rehearsal-e56af9a2/report.json`.
This is an operator-controls check, not another live-provider acceptance or a human
listening check. The first harness attempt left a SQLite copy connection open; that
local harness was corrected before the passing run. No application fix was needed.

The user expects the friend's UI handoff around 05:50. Preserve the current MP4 and
recorded revision while checking that diff. Re-record only if useful changes pass
affected checks and time permits; existing footage remains valid evidence of its
recorded revision. Stage presenter is still undecided.

Portable handoff: `backend/data/presentation/Astra-presentation-kit.zip` contains the
MP4/SRT, slide PDF/PNG, cue PDF/PNG, offline presenter HTML, script, upload text and
public evidence. Extract it before opening the HTML. The MP4 hash is unchanged;
explicitly selected files were checked against seven configured secret values with
zero matches. This small kit complements the larger raw/source backup.

[HQ draft](https://hq.agents007.ai/submit) is saved with the project name, pitch, problem/value, working scenario, honest limitations, stack and public repository. No final submission has been sent. User will upload the final MP4 to YouTube as **Unlisted** and provide the link.

At 05:26 the user explicitly selected **Best ElevenLabs Use**. The checkbox is now
enabled in the saved draft and remains enabled after reload; the existing public
showcase preference was preserved. HQ still disables Submit until the video URL is
provided. Opting in is not a completed submission.

The repository is `https://github.com/Zsadigzade/Astra`. The live-demo field stays blank: local Codex sign-in and a local dashboard access token are not a public hosting setup. Never expose the local development server as a public demo.

Before final submission: watch the complete MP4 with sound, upload Unlisted, verify playback signed out, paste the exact link, confirm the current source revision is public, then submit and retain confirmation. The form allows edits until 07:14. The 60-second pitch and jury answers are in [script.md](script.md).

The current HQ topic requires an executed transaction and allows a paid API as counterparty. Use the independently recorded Apify charge as the external transaction evidence; retain the explicit simulated-escrow limitation. No live Masumi funding, registration, escrow or settlement is claimed.

## Backup and final media verification

Six separate silent takes are saved under `backend/data/video/takes/`, named after the six cases in the table. `takes-manifest.json` records their deal IDs and SHA-256 hashes. Original speech remains in the capture audio directory. The curated backup is `backend/data/release-backup-1d9173c.zip`; its manifest is beside the final video. It excludes `.env`, authentication stores, HQ sessions, private configuration and service logs. This is a second local copy, not an off-device backup.

The full final MP4 played through in Edge: 89.021333 seconds, 2,669 decoded video frames, zero dropped frames, no stalls or page/media errors, and decoded audio. FFprobe confirms 1920 x 1080, constant 30/1 fps, H.264/yuv420p and AAC stereo/48 kHz. Measured speech is -16.32 LUFS integrated with -1.38 dBTP true peak. Representative frames for every chapter were visually checked for readable outcomes, labels, captions and private information. Browser playback does not replace the uploader's human listening check.

Final MP4 SHA-256: `dce23394eceef8db3f01b046d97665c7bad7912276c2898e42ad8246d46810e6` (8,648,242 bytes). Read-only source hashes confirm all 91 application/dependency files match the recorded snapshot; `revision-resolution.json` explains the capture harness's base-revision label.
