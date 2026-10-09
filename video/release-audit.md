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
