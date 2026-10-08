# The Haggle recording and export handoff

Prepare one evidence-complete take per act before assembling the [1:55 script](script.md). Final footage follows R02's three consecutive runs in the selected profile, R05's 1920×1080 readability check and the V03 feature freeze. Existing automated or fallback-profile tests do not complete those gates.

## Recording requirements

1. Record the revision, payment/model/data/voice modes, guard cap, approval threshold, task budget and start balances with each take. Record provider fallbacks as they occur. Keep credentials, account menus and private notifications out of capture.
2. Use the full actual event sequence as the master. Save raw footage separately from edit copies. Keep one complete backup of each working act; a screenshot or a synthetic sequence does not count as backup footage.
3. Show each act's evidence from the storyboard. Keep the same deal ID through a take and retain enough time to read the guard reason and outcome. A separate approval/decline take is useful for acceptance but is not a fifth act in the two-minute cut.
4. Record speech on a separate track if possible. Use one audible speaker at a time. The voiceover timing already includes the four-act explanation; any agent speech must fit inside the same time slots. Text fallback must remain readable.
5. Only after the dashboard settles, choose crops, zoom, theme and cursor movements. Verify labels, negotiation, approvals, guard decisions and outcomes in the actual 1080p capture. Preserve SIMULATED/STAGED labels in any crop.

## Act 3 operation

Use the existing runner described in the [README](../README.md#run). From `backend/`, `uv run python scripts/up.py --crash` starts the seller and buyer, deliberately crashes the buyer after its first lock and restarts only the buyer once. In another terminal, `uv run python scripts/act.py honest` starts the deal. The dashboard may attach to these services.

Start this runner only after the prior session has finished and released its ports. Keep the same ledger and seller alive across the staged buyer restart. Do not use `--reset` during recovery. Preserve the buyer exit/restart output and the `already_paid` event with its matching deal and escrow reference. Retain an explicit editorial STAGED label after restart: the recovered task uses `honest`, so its event flag alone is insufficient to label the entire crash sequence.

Each rehearsal profile needs its own disposable SIMULATED ledger; preserve unfinished payments. Switching to or from Masumi requires completed deals, service restarts between modes and separate ledgers. Act 4 is always SIMULATED.

## Take and rehearsal record

Fill one row per real take; no takes have been recorded by this preparation task. Use an ignored local media folder such as `backend/data/video/` and retain the approved export separately for upload.

| Act and take | Revision and profile | Deal and escrow reference | Raw file | Proof and labels checked | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | Pending | Pending | Pending | Quote, lock, verified delivery, release, data source | Pending |
| 2 | Pending | Pending | Pending | 25 blocked at cap 10, no debit, scripted and STAGED | Pending |
| 3 | Pending | Pending | Pending | Actual buyer crash, same reference, one payment, STAGED | Pending |
| 4 | Pending | Pending | Pending | Failed checks, refund, no seller credit, SIMULATED/STAGED | Pending |

For R02, log three consecutive successful runs **of each act** in the exact selected profile. For V02, time a complete four-act narration and evidence walkthrough. Record actual duration and trim to at most 2:00; the planned timestamps are not a measured rehearsal. Preserve the guard, crash and limitations if a cut is needed. Shorten repeated negotiation lines or waits first.

## Captions and export

[narration-draft.srt](narration-draft.srt) contains the baseline voiceover text. It is an editing input, not a finished subtitle track. Record the final voiceover, update disclosures to match the selected takes, then retime every cue to speech. Recheck names, prices and labels after retiming.

Export the approved timeline as a 1920×1080 MP4, H.264 video with `yuv420p`, AAC audio and a consistent frame rate (30 fps is the working target). Enable web playback/fast start. Export captions alongside the video, or burn them in if the submission player cannot show sidecar captions. Keep captions clear of payment and staging labels.

Inspect the finished file with:

```powershell
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,pix_fmt,avg_frame_rate -of json backend/data/video/the-haggle-final.mp4
```

The file must last at most 120 seconds. Watch the entire exported file with audio: confirm readable text at 1080p, caption sync, no clipped speech, no missing media/black gaps, and accurate SIMULATED/STAGED/provenance disclosures. ffprobe checks metadata, not those viewing requirements.

## Release completion

- V01: written script and storyboard; timing remains an estimate until rehearsal.
- V02: backup footage plus timed rehearsal, after R02; pending.
- V03: final takes after the feature freeze, with visible labels; pending.
- V04: edited video, final voiceover/captions and inspected export; pending.
- V05: keep run steps, architecture, environment template, handoff and limitations aligned with the final profile. Retain the no-key startup path.
- V06: [audit evidence](release-audit.md); rerun scans for the final revision and review any added media before publication/upload.

The submission team still needs to upload the approved video and check both repository and video links without signing in. Preparing this package does not complete V02–V04 or submit anything.
