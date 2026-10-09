# Submission release audit - 9 October 2026

Recorded application revision: **`1d9173c7325482bc204bfc145376963d96bb6cdc`**. The release documentation and informational scrape-count correction accompany this report. Application behavior in the recording matches 91 application/dependency file hashes; the capture harness's base label is resolved by its saved source patch and `revision-resolution.json`.

## Source and access checks

Presentation follow-up at 05:28: 212 publishable files checked against seven local
secret values with zero matches; reachable contents checked at 72 commits / 778 blobs
(HEAD `962e91b`; additional local checkpoint commits included). Gitleaks's updated
working-source scan has one reviewed finding: the existing nonsecret Apify run-reference
line. All 61 local Markdown links in the changed documentation resolve. The 92 checked
application/dependency files still match the captured source; only presentation and
documentation files changed in this pass. The portable kit's 12 asset files also pass
the private known-secret comparison, and its ZIP integrity check passes.

The new presenter HTML passed Edge checks for timer start/pause/reset, warning after
60 seconds, hiding/restoring notes and full-frame stage layout. Stage/cue PDFs each
have one page; rendered PNGs were visually reviewed. User authorized the ElevenLabs
side-prize option; its draft save was reload-verified. YouTube and final submission
are still pending. A later UI handoff requires its own affected checks.

- Gitleaks 8.30.1 with full redaction: Git changes across all locally reachable refs, complete reachable blob/commit contents, and the publishable working-source snapshot. At the 05:08 scan: **69 commits, 765 blobs, 210 source files**. The Git change scan reported 48 commits with scannable changes; the full-object pass covers all 69 reachable commits.
- Findings: 2 in Git changes, 11 in complete historical objects, 1 in the working snapshot. Every source line was individually reviewed: all are nonsecret Apify run references already documented in the repository. No suppressions were added and scanner exit 1 was investigated, not called a zero-finding result.
- Seven nonempty locally configured secret values were checked privately against source and history: **zero matches**. Generated overlay/caption text and recording/evidence JSON also had zero matches across 26 files. Credentials were never copied into the media package.
- Unauthenticated GitHub API access returned **200**, `private: false`, `visibility: public`. Final remote-commit publication evidence is retained locally as `backend/data/release-audit/publication-verification.json` after publishing; this report does not infer publication from a local commit.
- Repository refs included main and the existing `feat-mais-masumi-payments` branch; no inaccessible/deleted host-side refs are claimed as scanned. Scanner logs and copied historical content remain ignored under `backend/data/release-audit/`.

## Recorded behavior and media

- Full backend suite after the approval prompt fix: **579 passed (36.22 s)**. Frontend: **63 passed**, production build passed. No application source changed after the recording; only documentation and the rehearsal's paid-scrape-count notice changed.
- `backend/data/r-rehearsal-4f36a7e8/report.json`: **passed: true**, four acts plus approval/decline. 18 live Max / 24 live Viktor turns, 49 served speech clips, no provider fallbacks or page errors. One intentionally crash-interrupted clip is unavailable. Simulated balances conserve 100 and finish at 77/23/0.
- Final MP4: **89.021333 s**, 8,648,242 bytes, 1920 x 1080, H.264/yuv420p, constant 30/1 fps, AAC stereo/48 kHz, fast start and burned captions. Full Edge playback reached the end with decoded audio, 2,669 video frames, **zero dropped frames, stalls, media errors or page errors**.
- Measured audio: **-16.32 LUFS integrated**, **-1.38 dBTP** true peak. Frames from every chapter were inspected for legibility, SIMULATED/STAGED disclosure, outcomes, captions and private information. The capture contains only the app viewport, without browser chrome, account pages or private desktop windows. This is sampled visual review plus full automated playback; the uploader's human listening check remains required.
- MP4 SHA-256: `dce23394eceef8db3f01b046d97665c7bad7912276c2898e42ad8246d46810e6`. [Public nonsecret evidence](evidence.json) records deal IDs, event counts, code revision and provider charges.
- Six separate raw silent takes, the uncut master, original speech and nonsecret evidence are retained. The curated local backup excludes configuration, credentials, authentication stores, HQ sessions and service logs. It is not an off-device backup.

## Remaining external acceptance

The signed-in HQ requires a **90-second Unlisted YouTube video** and a **60-second pitch**; these supersede older public two-minute instructions. The project draft is saved. User will upload the MP4 and provide its link. Final submission, signed-out video playback and submission confirmation are not yet complete.

Apify metadata records actual paid API usage, including USD 0.110573 for Act 1. This is distinct from **SIMULATED agent escrow**. Live Masumi funding, registration, escrow and on-chain settlement are unverified. No public application deployment or real payment to Viktor is claimed.

## Historical audits (superseded snapshots)

# The Haggle repository release audit

Checked **2026-10-09 00:41 +02:00**, against HEAD `318d841e8ee35eeffdad85e82b82b8bee42edf90` and all locally reachable refs. **No credential findings remain after review. The repository is public.** This result covers the scanned snapshot; rerun for the final release revision because implementation work is continuing.

## Scope and result

| Check | Evidence |
| --- | --- |
| Remote coverage | `git ls-remote --heads --tags origin` returned `main` at `318d841e8ee35eeffdad85e82b82b8bee42edf90` and `feat-mais-masumi-payments` at `199fd719b00bbb6b040024a4a0ad9ab55802e0e0`, matching local refs; no remote tags. Local repository is not shallow. |
| Full reachable content | Enumerated `git rev-list --objects --all`: 48 commit objects and 476 unique file blobs, including both branches and local auxiliary refs. Scanned complete contents and commit messages, including merge-created content, with Gitleaks 8.30.1 default rules. |
| Git change scan | Gitleaks `git --log-opts="--all --full-history"` scanned 32 commits with scanable changes. The separate object scan above covers all 48 reachable commits; the Git diff count alone is not the full-history count. |
| Working source snapshot | Scanned 159 tracked and nonignored untracked files, including in-progress edits. Local credentials, runtime caches, dependencies and media were excluded from this publishable-source snapshot. |
| Known local credentials | Checked all reachable blob/commit contents and working source against five nonempty configured secret values read privately from `.env`: zero matches. Values were never printed or included in reports. |
| Findings reviewed | One generic-key finding in history, seven occurrences across historical blobs and one in the working snapshot all refer to the documented Apify run ID `ZNboU2b0EHUJgFaEQ`. Exact source-line checks confirmed each. This is a run reference, not an authentication token. No rule or path suppressions were added. |
| Public access | GitHub metadata reports `visibility: public`. A separate HTTPS request to `https://api.github.com/repos/Zsadigzade/Astra` without authentication returned HTTP 200 and `private: false`. No visibility change was needed. |

Gitleaks 8.30.1 was downloaded from its official GitHub release and its Windows archive SHA-256 matched the release checksum file before execution. Scan logs/reports are redacted. Scanner findings cause exit code 1 even for the reviewed run-ID false positive; that exit code was investigated, not reported as a zero-finding scan.

The initial scan covered 46 commits and 475 blobs; the 00:41 recheck included two new local checkpoint commits and one additional blob. HEAD and the checked remote branch tips were unchanged. All seven whole-object findings were rechecked against their source lines.

Local audit materials are ignored under `backend/data/release-audit/`: `history-gitleaks.json`, `objects-gitleaks.json`, `worktree-gitleaks.json`, `summary.json`, the object-to-path index and the snapshot helper. They are not release assets. The tool binary and copied historical contents also remain there.

## Recheck at release

Use Gitleaks with full redaction and inspect only locations/rule IDs before reviewing any match. From the repository root:

```powershell
gitleaks git . --log-opts="--all --full-history" --redact=100 --ignore-gitleaks-allow --no-banner --report-format=json --report-path=backend/data/release-audit/history-gitleaks.json
```

Also scan a snapshot of `git ls-files --cached --others --exclude-standard` and the full blob/commit contents reachable from `git rev-list --objects --all`. For this local workspace, `.venv/Scripts/python.exe backend/data/release-audit/scan_objects.py` recreates those snapshots and repeats the configured-secret check; then run `gitleaks dir` on its `objects` and `worktree` folders with the same redaction/report options. Compare remote refs again so a newly pushed branch is not silently omitted. Do not scan the whole runtime folder as if it were publishable source: it intentionally contains private local configuration and generated artifacts.

Review each new finding; do not suppress a whole file to hide a false positive. If a real credential is found, stop release, revoke/rotate it and coordinate history cleanup with its owner. A scanner cannot prove absence of every possible secret. This audit does not cover deleted remote branches, inaccessible host-side refs, issue attachments or a future video export.

Before upload, inspect the actual footage for account details/credentials and check the final repository and video links without signing in. The repository check here completes V06 for this snapshot; the final video and S02 link acceptance remain pending.

## Local release recheck — 2026-10-09 02:40 +02:00

Base HEAD `f355fccd33a31b54261ad1babc2a5d9b62966a0a` plus the local release-check edits:
62 reachable commits and 674 blobs inspected. Gitleaks Git scan reported one historical
finding; the full object scan reported nine occurrences. Each source line was inspected
and contains the already-documented nonsecret Apify run reference. Five configured secret
values had zero source/history matches. The final 197-file working-source scan reported one
generic-key finding on the new report's three Apify run IDs; those IDs were checked against
the actual delivery provenance and are nonsecret references. No suppressions were added.
Remote `main` matches HEAD; `feat-mais-masumi-payments` is `4f1db10c517456b252c7cc510319f0e43d5a996f`.
Unauthenticated GitHub API check again returned HTTP 200 and `private: false`.

Dependency audits: frontend zero known vulnerabilities after Vite 6.4.4 update; production
Python lock export audited 22 packages with zero known vulnerabilities. Live provider and
browser evidence, configuration changes and deployment limits are in the
[local release check](../memory/status/production-readiness.md).
No final media inspection, commit, push or deployment is claimed. Rescan after further edits.
