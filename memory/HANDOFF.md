# Handoff — state of `main`

updated: 2026-10-08 22:19 · ziya

## Latest changes on main
- `036105e`: Masumi readiness checks reject incomplete setup; node-only bootstrap and README runbook.
- `1244aa6`: unassigned checklist, workspace cleanup, confirmed removal of agent-instruction files.

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
- Last test run at 22:14: `uv run pytest` → 58 pass (25 new readiness cases).
  Dashboard stub build was previously verified; no new live integration was tested during cleanup.

## Work queue
- [plan.md](../plan.md): 5 completed baseline items and 30 open, unassigned tasks with IDs.
  Groups: D dashboard/startup, M Masumi, I data/agents/voice, R reliability, V video/release, S submission.
- D01 (Act 1 on every laptop) remains unchecked; one-laptop/test success does not pass that gate.
- Cutoffs: no Masumi node by 23:30 → SIMULATED video; no live escrow by 01:00 → same fallback.
  Feature freeze 04:00; video/repo 06:30; target submission 07:00, hard deadline 07:14 (Prague time).
- Team task split is pending. Other status files still report 17:15 kickoff; no new assignment inferred.
- README links to setup, checklist and memory. Generated folders are hidden in Explorer, not deleted.

## Known broken / risky
- Local .env checked at 22:19: PAYMENTS_MODE=simulated, Masumi URL is local; node key,
  seller identifier/vkey and Blockfrost Preprod key are missing. Hosted node status is unconfirmed.
- OPENAI_API_KEY is missing locally; Max's `openai` mode is untested live; Viktor stays scripted.
- Flats are sample data (`source: "sample"`); TTS untested against live API.
- Seller keeps jobs in memory: never restart the seller mid-deal (TRAPS.md).
- Use separate LEDGER_PATH files for simulated and real payments; ledger does not enforce mode isolation.
- Act 4 refund stays SIMULATED even if Acts 1 and 3 use Preprod. Real release is scheduled, not immediate.
- Reset disposable simulated data only: `scripts/up.py --reset` deletes `data/buyer.db`;
  it does not follow a custom LEDGER_PATH. Never reset a ledger with unfinished payments.
