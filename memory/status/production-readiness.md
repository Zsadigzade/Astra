# Recording release - 9 October 2026

The current submission profile is **codex/codex/live Apify/ElevenLabs/SIMULATED escrow**, STRICT_LIVE enabled. Recorded application revision: `1d9173c7325482bc204bfc145376963d96bb6cdc` (the merged baseline plus the approval-path prompt fix).

**05:25 presentation update:** the friend owns ongoing UI/UX work, expected around
05:50. Keep the recorded MP4 unchanged while checking the handoff. Remaining P02
Pause/Resume/audio/replay/safe-reset controls passed in an isolated session without
new provider calls; report `backend/data/r-rehearsal-e56af9a2/report.json`. Stage slide,
printable one-page cues and rehearsal timer are prepared in `video/presenter.html`
and `backend/data/presentation/`. Human audio review, chosen speaker/timed pitch,
new UI revision acceptance, YouTube link and final submission remain open.

- **579 backend tests**, **63 frontend tests**, and production build pass. The backend suite was repeated after the prompt fix: 579 passed in 36.22 seconds.
- Fresh recorded acceptance `backend/data/r-rehearsal-4f36a7e8/report.json`: **passed: true**, all four acts plus approve/decline, zero browser page errors and provider fallbacks. 18 Max / 24 Viktor live turns, 49 served speech clips; one intentional crash-interrupted clip is unavailable. This is one run per case, not a three-repeat claim.
- Actual buyer crash: PID 4584 exits with code 1, resumes as 24024; seller 28884 stays running. Same deal, one lock, one `already_paid`, one release. Final simulated balances 77 / 23 / 0.
- Real Apify billing metadata is preserved: four successful runs report roughly USD 0.11 each. Act 1: USD 0.110573, 22 charged results. These are provider charges, not agent escrow or a Masumi transfer. Simulated refunds do not refund provider charges.
- Recording laptop services are healthy on 8000/8001/5173, live modes selected, guard 10/8, balances 93 / 7 / 0. Dashboard returns 200; unauthenticated buyer balances return 401. Existing active laptop services remain running; capture's private services were stopped.
- Export: `backend/data/video/the-haggle-final.mp4`, approximately **89 seconds**, 1080p H.264/yuv420p, constant 30 fps, AAC stereo, normalized speech and burned captions. Uncut master and original speech are retained separately.
- Authenticated HQ instructions supersede the public site: **90-second video**, **Unlisted YouTube**, **60-second pitch**, presentations 09:30, submit before 07:14; target 07:00. Project draft is saved. User is uploading the video; final submission is pending the link.

[Operator/take/submission handoff](../../video/production.md), [pitch](../../video/script.md), [nonsecret evidence](../../video/evidence.json), [final audit](../../video/release-audit.md).

No public application hosting or live Masumi escrow is claimed. The local model runtime requires ChatGPT sign-in, and dashboard tokens remain local. The no-key sample startup path stays supported. Only the informational rehearsal scrape-count notice changed after recording: one pass can start four scrapes, not three, because staged junk also uses real data.

## Historical 02:40 release check (superseded)

# Local release check — 2026-10-09

> **Superseded 03:11** by the STRICT_LIVE profile: live con/junk, all-live Viktor lines, auth, rate limit
> and durable seller store. Rehearsal `backend/data/r-rehearsal-965ff982` passed (one run per act +
> approve/decline, codex/codex/apify/elevenlabs/simulated). Details in [HANDOFF](../HANDOFF.md).

Checked at 02:40 Europe/Budapest against base revision
`f355fccd33a31b54261ad1babc2a5d9b62966a0a` plus this working tree.
User selected live data, agents and voices with SIMULATED payments. Deployment destination
was not specified; this acceptance covers the local Windows application, not public hosting.

## Configuration and changes

- Ignored root `.env`: `LLM_MODE=codex`, `SELLER_LLM_MODE=codex`, `APIFY_MODE=apify`,
  `TTS_MODE=elevenlabs`, `PAYMENTS_MODE=simulated`, `APIFY_ALLOW_STALE_CACHE=0`,
  `CRASH_AFTER_LOCK=0`. Existing credentials were retained privately, not rotated or published.
- Fresh Codex probes passed for both agents; two fresh ElevenLabs samples passed.
- Vite updated from 5.4.11 to 6.4.4 with the lockfile. The former audit reported high/moderate
  issues; the new audit reports zero. Upstream's Windows path advisory lists 6.4.3 as patched:
  [Vite advisory](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff).
- Rehearsal supports explicit seller/data modes and one to three repeats. It rejects model
  fallback and cached delivery as live acceptance, retaining intentional scripted acknowledgements
  and staged con behavior. Updated outdated browser selectors for the current tabbed dashboard.
- README now states that every live rental delivery attempts a paid scrape, including exact
  cache matches. Successful scrapes refresh the matching cache. Offline template defaults remain.

## Verification

| Check | Result |
| --- | --- |
| Backend | 541 tests passed, 32.25 seconds, `uv run --locked pytest -q --tb=short` |
| Frontend | 50 tests passed; Vite 6.4.4 production build passed |
| Dependencies | `npm audit`: zero; pinned production Python dependency audit: 22 packages, zero known vulnerabilities |
| Live profile | Both subscription agents, live Apify and ElevenLabs; one run of every act plus approval and decline passed |
| Browser | Eight 1920×1080 Edge screenshots, zero page errors/overflow; deal and pending-approval screenshots visually reviewed |
| Recovery | Actual buyer crash, seller survived, one escrow lock and one `already_paid`; no duplicate payment |
| Provider usage | 17 Max and 19 Viktor Codex turns; 45 available speech clips served over HTTP; zero provider fallbacks |
| Intentional interruption | One crash-interrupted speech line unavailable, explicitly recorded; not counted as successful speech |
| Accounting | 77 buyer / 23 seller / 0 escrow; conserved 100 SIMULATED tADA |
| Secrets/public access | 62 reachable commits, 674 blobs; five configured secrets found nowhere in source/history. Gitleaks flags reviewed as the known run reference. Unauthenticated GitHub check: HTTP 200/public |

Reproduce from `backend/` (provider quota applies; up to three scrapes at a requested $1.10 cap each):

```powershell
uv run --locked --with playwright python scripts/rehearse.py --browser --seller-mode codex --data-mode apify --repeats 1
```

Evidence: `backend/data/r-rehearsal-712703a0/report.json`, ledger, logs and screenshots.
All services started by this rehearsal were stopped. Earlier attempts `18b29349` and
`1fabb665` failed on obsolete/ambiguous browser selectors before launching any task.
Python audit: `backend/data/production-pip-audit.json`. Secret audit: `backend/data/release-audit/`.

| Case | Deal | Outcome |
| --- | --- | --- |
| Normal | `56e75870f9c84f3585a5` | Released at 7, 20 LIVE APIFY rentals |
| Con | `f8b899d447f04942b096` | Blocked before payment, STAGED |
| Recovery | `576d02371d684c879bfb` | Released once after actual buyer restart |
| Junk | `756a2976bde145519146` | Refunded, STAGED / SAMPLE |
| Approve | `ecca1240453d4cf38012` | Released at 9 after dashboard approval |
| Decline | `727ca4aeb06542f1b4d1` | Blocked without payment |

Fresh Apify runs: `gxIHSC0ngiMihK6RT`, `lnMusRPTYACdA5jtQ`, `e2JwuG2Ti0np3WUAI`.
Latest fallback cache contains 20 verified rentals, fetched at `2026-10-09T00:38:57.917431+00:00`,
dataset `27dJyGjuzNyamrGEL`. Original legacy cache remains intact.

## Activation and remaining limits

The pre-existing services on 8000/8001/5173 were preserved. Their health checks still report
scripted Viktor and cached Apify. After existing deals finish, stop that session in its owning
terminal/launcher and restart `npm start`, or choose **Configured (.env providers)** in the
Windows launcher and enable provider usage. Do not restart the seller during a funded deal.
The launcher reads this checkout; no EXE rebuild is needed for these changes.

This is local live-provider acceptance, not public-production sign-off. Public deployment
still needs authenticated/authorized control endpoints, rate limits, durable seller jobs,
a supported hosted agent runtime, persistent storage and HTTPS/static serving. CORS is not
authentication. No public deployment, commit, push, video upload or real payment occurred.

Masumi remains deliberately SIMULATED; full node configuration check fails because
`MASUMI_AGENT_ID` and a valid `SELLER_VKEY` are absent. Registration, balances and live escrow
were not reverified. One run per act does not satisfy the three-repeat recording-profile gate.
This browser pass verified controls/layout and speech HTTP delivery, not a new audible-playback
rehearsal or measured two-minute video. Existing audio unit tests passed.
