# Handoff — state of `main`

updated: 2026-10-08 22:32 · ziya

## Latest changes on main
- `036105e`: Masumi readiness checks reject incomplete setup; node-only bootstrap and README runbook.
- `1244aa6`: unassigned checklist, workspace cleanup, confirmed removal of agent-instruction files.
- I path: Apify rental/cache adapter, Max fallback labels, ElevenLabs checks and ordered audio playback.

## What works
- Product "The Haggle": buyer Max (:8000, `buyer/`) haggles with seller Viktor (:8001, `seller/`),
  wallet guard pays into escrow, verifier checks 20 Praha 7 flats, release or refund. SSE `/events`.
- One command: `uv run python scripts/up.py [--reset] [--crash]`; terminal demo: `scripts/act.py honest|con|junk`.
- All 4 acts verified live in SIMULATED mode: deal at 7 released; con at 25 BLOCKED (cap 10);
  crash after paying → buyer auto-restarts → `already_paid`, deal released, paid once; junk refunded.
- Guard: cap 10, budget 20, approval >8, never pays a deal twice. Crash recovery: funded, errored and
  awaiting-approval deals resume; seller start response stored (`start_json`) and reused.
- Masumi mode (`PAYMENTS_MODE=masumi`): `shared/masumi.py` client, Dynamic pricing, idempotent lock,
  release = scheduled at unlockTime. Tested only against `tests/fake_masumi.py`.
- `LLM_MODE=openai`: Max on OpenAI Agents SDK, falls back to scripted Max per round on any error.
- Read-only Masumi checker: `--node-only` for bootstrap; default also checks local seller config.
  Fails incomplete setup; never claims registration, funding or live escrow was verified. README has setup steps.
- Apify source `swerve/sreality-scraper`: max 200 records, 90s default timeout, requested $1.10 run
  charge limit; strict Praha 7/monthly-CZK checks, labelled `apify_cached` fallback with provenance.
- ElevenLabs: bounded TTS/text fallback; voice discovery/synthesis checker; queue has Play/Stop/Mute,
  ordered playback, SSE deduplication and error skipping. Dashboard displays data/backend provenance.
- Validation at 22:30: 129 Python tests, 7 audio-queue tests, dashboard production build passed.
  Provider requests were mocked; no real scrape or speech was generated.

## Work queue
- [plan.md](../plan.md): 5 completed baseline items, I06 queue implemented, 29 tasks remain open.
  Groups: D dashboard/startup, M Masumi, I data/agents/voice, R reliability, V video/release, S submission.
- D01 (Act 1 on every laptop) remains unchecked; one-laptop/test success does not pass that gate.
- Cutoffs: no Masumi node by 23:30 → SIMULATED video; no live escrow by 01:00 → same fallback.
  Feature freeze 04:00; video/repo 06:30; target submission 07:00, hard deadline 07:14 (Prague time).
- Ziya owns I01-I06; Mais/Murad handle the other paths (exact split unspecified). Their status files
  still report 17:15 kickoff; no claim about their current progress is inferred.
- README links to setup, checklist and memory. Generated folders are hidden in Explorer, not deleted.

## Known broken / risky
- Local .env last checked for payments at 22:19: PAYMENTS_MODE=simulated, Masumi URL is local; node key,
  seller identifier/vkey and Blockfrost Preprod key are missing. Hosted node status is unconfirmed.
- User confirms no OpenAI API key was supplied; I03 live check and optional I04 remain blocked.
- At 22:32 APIFY_TOKEN still missing; at 22:30 ElevenLabs key/voice IDs missing. No real-data cache yet.
  Run `scripts/scrape_flats.py` after key entry; `scripts/voice_check.py --synthesize` after voice setup.
- Default flats stay SAMPLE and voices stay off; I01/I02/I05 live acceptance is still open.
- Seller keeps jobs in memory: never restart the seller mid-deal (TRAPS.md).
- Use separate LEDGER_PATH files for simulated and real payments; ledger does not enforce mode isolation.
- Act 4 refund stays SIMULATED even if Acts 1 and 3 use Preprod. Real release is scheduled, not immediate.
- Reset disposable simulated data only: `scripts/up.py --reset` deletes `data/buyer.db`;
  it does not follow a custom LEDGER_PATH. Never reset a ledger with unfinished payments.
