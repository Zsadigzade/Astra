# Memory map — index

Start with HANDOFF for current facts and plan.md for unassigned work. Status files are
owner-reported snapshots: check their timestamps before assuming someone has claimed a task.
DECISIONS and TRAPS preserve history; later entries may supersede earlier ones.

- [HANDOFF.md](HANDOFF.md) — current integrated state of `main` and validation limits. Read first.
- [DECISIONS.md](DECISIONS.md) — append-only decision log (what, why, who, when).
- [INTERFACES.md](INTERFACES.md) — contracts between components: endpoints, payloads, env vars, ports.
- [TRAPS.md](TRAPS.md) — append-only: what broke and how to avoid it.
- [status/ziya.md](status/ziya.md) — Ziya's last reported work and blockers.
- [status/murad.md](status/murad.md) — Murad's last reported work; owner maintains this file.
- [status/mais.md](status/mais.md) — Mais's last reported work; owner maintains this file.
- [status/reliability.md](status/reliability.md) — ledger mode isolation, verified tests and coordination with the runner session.
- [status/runner-reliability.md](status/runner-reliability.md) — startup ownership, safe reset and staged restart fixes; owner-reported validation.
- [../plan.md](../plan.md) — unassigned task checklist, deadlines and fallback gates.
- [../README.md](../README.md) — product overview, run instructions and honest limitations.
