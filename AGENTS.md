# AGENTS.md — Astra team memory map

Read this file before every task. It is the shared prompt for every coding agent on team MMZ
(Claude Code, Cursor, Codex, Copilot, ...). `CLAUDE.md` and `.cursor/rules/` point here.

Three humans work in parallel overnight, each driving their own agent. Agents do not share
chat history. **The `memory/` folder is the only shared brain.** If something is not written
there, the other agents do not know it.

---

## 1. Project context

- **Event:** Agents 0.0.7 "From Dusk Till Dawn" Hackathon #01, Prague, 2026-10-08 17:30 → 10-09.
- **Track:** Agentic Economy — an end-to-end scenario with agentic financial transactions.
- **Deliverable:** working code + a 2-minute video, due **07:14** (sunrise).
- **Judging:** E2E works 35% · value/track 25% · tech 20% · originality 10% · honest limitations 10%.
- **Team MMZ:** Ziya Sadigzade, Murad Shirinov, Mais Isifzade.
- **Stack:** Python, OpenAI Agents SDK, Masumi (Cardano Preprod) payments with escrow.
  The model comes from the `MODEL` env var (cheap default). Partner credits: OpenAI, ElevenLabs,
  Apify, Masumi.
- **Topic:** see `memory/DECISIONS.md` (candidates are in `TOPICS.md`).

---

## 2. The memory map

```
memory/
  MAP.md            index: one line per memory file, what it holds
  DECISIONS.md      append-only log of decisions (what, why, who, time)
  INTERFACES.md     contracts between components: endpoints, payloads, env vars, ports
  TRAPS.md          append-only: things that broke and how to avoid them
  HANDOFF.md        current state of the whole build, in one screen
  status/
    ziya.md         what Ziya + agent are doing right now
    murad.md        what Murad + agent are doing right now
    mais.md         what Mais + agent are doing right now
```

### Read order (every task)
1. `memory/MAP.md`, then `memory/HANDOFF.md`.
2. `memory/INTERFACES.md` if you touch anything another person consumes or produces.
3. `memory/TRAPS.md` before debugging anything.
4. Other people's `status/*.md` to avoid duplicate work.

Read only what the task needs. Do not load the whole folder "just in case".

### Write rules
| File | Who writes | How |
|---|---|---|
| `status/<you>.md` | only its owner | overwrite freely; at task **start** and **end** |
| `DECISIONS.md` | anyone | **append only**, newest at bottom, never edit past entries |
| `TRAPS.md` | anyone | **append only** |
| `INTERFACES.md` | the owner of that component | edit your own section; changing a contract someone else consumes = post in team chat first |
| `HANDOFF.md` | whoever merges to `main` | rewrite to reflect what `main` now does |
| `MAP.md` | anyone adding a memory file | one line per file |

Entry format for append-only files:
```
- 2026-10-08 21:40 · murad · <one-line fact>. Why: <reason>. (commit abc1234)
```

### Hard rules
1. **Before you start a task:** update `status/<you>.md` (task, files you will touch, ETA).
2. **When you finish a task:** update your status, append any decision or trap, and commit the
   memory change **in the same commit** as the code.
3. **Never write secrets** (API keys, wallet mnemonics, tokens) into memory, code or commits.
   Secrets live in `.env` only (git-ignored). Document the variable *name* in `.env.example`
   and `INTERFACES.md`.
4. **Facts, not plans.** Memory records what is true on `main` or what was decided. Hopes and
   TODOs go in your status file only.
5. **Keep files short.** HANDOFF ≤ 60 lines. Status ≤ 20 lines. If a file grows, summarise
   older entries; never delete a decision's *why*.
6. **Conflicts:** on a merge conflict in `memory/`, keep both sides' entries, then fix the order.
   Never resolve a memory conflict with "take mine".
7. **Unsure whether something is decided?** Check `DECISIONS.md`. Not there = not decided; ask
   your human, don't guess.
8. **Simulated money must be labelled.** Any fake or fallback payment path shows `SIMULATED`
   in the UI and logs. This is a judging criterion (honest limitations).

---

## 3. Git conventions

- `main` must always run the demo. Work on `feat/<name>-<thing>`, merge yourself once it runs.
- Pull `main` before you start and before you merge. Small commits, often.
- Commit messages: `feat:`, `fix:`, `docs:`, `mem:` (memory-only change), `chore:`.
- Never force-push `main`.

## 4. Status file template

```markdown
# <name> — status
updated: 2026-10-08 22:10
doing: <one line>
touching: <files / dirs>
blocked on: <nothing | who/what>
next: <one line>
done today:
- <short list>
```
