# Memory map — index

Start with HANDOFF for current facts and plan.md for unassigned work. Status files are
owner-reported snapshots: check their timestamps before assuming someone has claimed a task.
DECISIONS and TRAPS preserve history; later entries may supersede earlier ones.

- [HANDOFF.md](HANDOFF.md) — current state of `main` in one screen. Read first.
- [DECISIONS.md](DECISIONS.md) — append-only decision log (what, why, who, when).
- [INTERFACES.md](INTERFACES.md) — contracts between components: endpoints, payloads, env vars, ports.
- [TRAPS.md](TRAPS.md) — append-only: what broke and how to avoid it.
- [status/ziya.md](status/ziya.md) — Ziya's last reported work and blockers.
- [status/murad.md](status/murad.md) — Murad's last reported work; owner maintains this file.
- [status/mais.md](status/mais.md) — Mais's last reported work; owner maintains this file.
- [../plan.md](../plan.md) — unassigned task checklist, deadlines and fallback gates.
- [../README.md](../README.md) — product overview, run instructions and honest limitations.
