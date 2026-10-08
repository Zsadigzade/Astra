# Handoff — `main` and shared working tree

updated: 2026-10-08 23:26 · runner reliability (reconciled parallel session updates)

## Latest verified changes
- Subscription Max verified: live checker + Act 1 settled at 7, all three Max turns Codex, 20 cached flats verified, SIMULATED release. Five clips played; two TTS connection failures used text.
- 68 focused backend tests, 15 frontend tests and build pass; timeout/cancellation tests include real Windows process-tree cleanup. Local LLM_MODE=codex; no API key or SDK.
- Branch cleanup: only main remains locally and on origin; every removed branch tip was already merged.
- Local legacy root folders archived under ignored `backend/data/legacy-workspace/20261008-224546`; dependencies moved to `frontend/node_modules`. Frontend build and backend imports verified.

## Shared working tree (not yet committed)
- Ledger mode isolation and runner safety are implemented together. Both adapters bind the ledger's payment mode before recovery; reset uses the same mode inspection and preserves a timestamped backup.
- Verified: 213 full backend tests at 23:22, then 48 ledger/runner tests after the final integration. Runner session verified **215 full backend tests in 15.07s at 23:24**, including 27 runner regressions, with `LEDGER_PATH=:memory:` and isolated temporary test files. These are offline/fake-service checks; they do not complete all-laptop rehearsals or prove live Preprod escrow.
- Parallel model/configuration/dependency and dashboard changes remain owned by their active sessions. Coordinate through [reliability status](status/reliability.md), [runner status](status/runner-reliability.md) and [Ziya's status](status/ziya.md); preserve their edits and running services.

## What works
- Product "The Haggle": buyer Max (:8000, `backend/app/buyer/`) haggles with seller Viktor (:8001, `backend/app/seller/`), wallet guard pays into escrow, verifier checks 20 Praha 7 flats, release or refund. SSE `/events`.
- Backend commands run from `backend/`. One command: `uv run python scripts/up.py [--reset] [--crash]`; terminal demo: `scripts/act.py honest|con|junk`.
- All 4 acts verified live in SIMULATED mode: deal at 7 released; con at 25 BLOCKED (cap 10); crash after paying → buyer auto-restarts → `already_paid`, deal released, paid once; junk refunded.
- Guard: cap 10, budget 20, approval >8, never pays a deal twice. Crash recovery: funded, errored and awaiting-approval deals resume; seller start response stored (`start_json`) and reused.
- Masumi mode (`PAYMENTS_MODE=masumi`): `backend/app/core/masumi.py` client, Dynamic pricing, idempotent lock, release = scheduled at unlockTime. Tested only against `backend/tests/fake_masumi.py`.
- Model access is permanently subscription-only: `LLM_MODE=codex` uses local ChatGPT-authenticated CLI, with labelled scripted fallback; API SDK removed. Viktor and the STAGED Act 2 con stay scripted.
- Read-only Masumi checker: `--node-only` for bootstrap; default also checks local seller config. Fails incomplete setup; never claims registration, funding or live escrow was verified. README has setup steps.
- Repository layout is a frontend/backend monorepo: Python code under `backend/app/`, React under `frontend/`.
- Apify source `swerve/sreality-scraper`: targets Praha 7, max 200 records, 90s timeout, requested $1.10 run charge limit; strict Praha 7/monthly-CZK checks, labelled `apify_cached` fallback with provenance.
- ElevenLabs: bounded TTS/text fallback; voice discovery/synthesis checker; queue has Play/Stop/Mute, ordered playback, reset-safe SSE deduplication and a 10s stalled-clip watchdog; data/backend provenance shown.
- 23:09: 144 Python tests, 15 frontend tests and production build pass. Live Apify returned 20 valid rentals. Real HTTP Act 1 in Edge verified 20 cached listings, SIMULATED release, and seven live ElevenLabs clips played without overlap/errors. Separate browser checks pass replay/reset IDs, missing clips, Stop/Mute.

## Work queue
- [plan.md](../plan.md): 5 completed baseline items; I01/I02/I03/I05/I06 complete; 25 tasks remain open. Groups: D dashboard/startup, M Masumi, I data/agents/voice, R reliability, V video/release, S submission.
- D01 (Act 1 on every laptop) remains unchecked; one-laptop/test success does not pass that gate.
- Cutoffs: no Masumi node by 23:30 → SIMULATED video; no live escrow by 01:00 → same fallback. Feature freeze 04:00; video/repo 06:30; target submission 07:00, hard deadline 07:14 (Prague time).
- Ziya owns I01-I06; Mais/Murad handle the other paths (exact split unspecified). Their status files still report 17:15 kickoff; no claim about their current progress is inferred.
- README links to setup, checklist and memory. Generated folders are hidden in Explorer, not deleted.

## Known broken / risky
- 23:04 Masumi node DEPLOYED on Railway (project `mellow-energy`, services `masumi-payment-service` + `masumi-psql-database`). URL `https://masumi-payment-service-production-96e0.up.railway.app/api/v1`. Postgres online; payment service image was still building at 23:04. 23:20: deploy restart-loops on an upstream Dockerfile bug (see TRAPS 23:20); patched fork `Zsadigzade/masumi-payment-service` ce8cfdb5; Railway source switched to the fork and rebuilt at ~23:28. `/health` 404, `masumi_check.py --node-only` not yet run (M01 open). Blockfrost Preprod project `astra-masumi-preprod`. Local .env: MASUMI_PAYMENT_URL = hosted URL, MASUMI_API_KEY = Railway ADMIN_KEY, MASUMI_NODE_ENCRYPTION_KEY, BLOCKFROST_API_KEY_PREPROD; keys are shared out of band, never committed. PAYMENTS_MODE=simulated; seller vkey missing; wallets unfunded. Railway ENCRYPTION_KEY: ziya confirmed at 23:30 that it was not leaked.
- No OpenAI API token will be supplied; `codex login` + `scripts/llm_check.py` replace API-key setup. Ziya's 23:25 update reports the live subscription checker and Act 1 passed; I03 is complete. Optional Viktor subscription work remains separate.
- Keys are now configured locally; Brian/Callum voices verified. Local APIFY_MODE=cached, TTS_MODE=elevenlabs. Other laptops: `scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ` rebuilds the ignored cache without another paid run. Template defaults remain SAMPLE/text; copy keys privately and select voice IDs.
- Seller keeps jobs in memory: never restart the seller mid-deal (TRAPS.md).
- Use separate LEDGER_PATH files for simulated and real payments. 23:22: adapters now enforce a persisted ledger mode before startup/resume; legacy history is checked and mixed/unknown payment activity rejected. Mixed or unidentifiable legacy payment history must be preserved and investigated; do not reset it to bypass the check.
- Act 4 refund stays SIMULATED even if Acts 1 and 3 use Preprod. Real release is scheduled, not immediate.
- From `backend/`, `scripts/up.py --reset` archives the configured LEDGER_PATH to a timestamped `.bak`. It rejects unfinished deals, held escrow, Masumi/mixed history and SQLite sidecars; simulated mode only. Runner checks occupied ports before reset/startup, cleans up only its children, and clears the crash flag for one staged buyer restart. See `memory/status/runner-reliability.md` for regression results.
