# Local release check — 2026-10-09

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
