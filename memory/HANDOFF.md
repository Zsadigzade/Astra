# Handoff — state of `main`

updated: 2026-10-08 22:35 · codex

## What works
- Product "The Haggle": buyer Max (:8000, `backend/app/buyer/`) haggles with seller Viktor (:8001, `backend/app/seller/`),
  wallet guard pays into escrow, verifier checks 20 Praha 7 flats, release or refund. SSE `/events`.
- Backend commands run from `backend/`. One command: `uv run python scripts/up.py [--reset] [--crash]`;
  terminal demo: `scripts/act.py honest|con|junk`.
- All 4 acts verified live in SIMULATED mode: deal at 7 released; con at 25 BLOCKED (cap 10);
  crash after paying → buyer auto-restarts → `already_paid`, deal released, paid once; junk refunded.
- Guard: cap 10, budget 20, approval >8, never pays a deal twice. Crash recovery: funded, errored and
  awaiting-approval deals resume; seller start response stored (`start_json`) and reused.
- Masumi mode (`PAYMENTS_MODE=masumi`): `backend/app/core/masumi.py` client, Dynamic pricing, idempotent lock,
  release = scheduled at unlockTime. Tested only against `tests/fake_masumi.py`.
- `LLM_MODE=openai`: Max on OpenAI Agents SDK, falls back to scripted Max per round on any error.
- Read-only Masumi checker: `--node-only` for bootstrap; default also checks local seller config.
  Fails incomplete setup; never claims registration, funding or live escrow was verified. README has setup steps.
- Verification after the layout change: `cd backend && uv run pytest` → 58 pass; `cd frontend && npm run build` → pass.
- Repository layout is a frontend/backend monorepo: Python code under `backend/app/`, React under `frontend/`.

## Work queue
- [plan.md](../plan.md) is the unassigned task checklist, including deadlines and fallback gates.
  The team will split the remaining tasks later; completed code is separate from live checks.
- README links to setup, the checklist and memory; VS Code/Cursor hides generated folders.

## Known broken / risky
- No Masumi node yet: money is SIMULATED; masumi mode never ran against a real service.
- No OpenAI key: `openai` mode untested live; Viktor has no LLM mode (scripted only).
- Flats are sample data (`source: "sample"`); TTS untested against live API.
- Seller keeps jobs in memory: never restart the seller mid-deal (TRAPS.md).
- Use separate LEDGER_PATH files for simulated and real payments; ledger does not enforce mode isolation.
- Reset demo data from `backend/`: `scripts/up.py --reset` (deletes `backend/data/buyer.db`).
