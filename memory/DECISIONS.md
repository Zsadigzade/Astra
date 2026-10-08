# Decisions — append only

Format: `- YYYY-MM-DD HH:MM · who · <decision>. Why: <reason>.`

- 2026-10-07 21:00 · ziya · Track = Agentic Economy. Why: best fit for team skills + Masumi partner credits.
- 2026-10-07 21:00 · ziya · Stack = Python + OpenAI Agents SDK; model from `MODEL` env var, cheap default. Why: fastest path, OpenAI credits.
- 2026-10-07 21:00 · ziya · Payments = Masumi Preprod escrow; fallback = labelled SIMULATED ledger. Why: real E2E if testnet works, honest fallback if not.
- 2026-10-07 21:00 · ziya · Repo private during build, flipped public at submission. Why: judges need access to code.
- 2026-10-08 17:15 · ziya · Team memory lives in `memory/`, rules in `AGENTS.md`. Why: three agents, no shared chat history.
- 2026-10-08 19:32 · ziya · Topic = #1 Agents Hire Agents, with #2 firewall rules (budget cap, human approval above threshold) inside the buyer. Why: hero moment = money moving between agents; customer = busy human delegating work; 3 components fit 3 people.
- 2026-10-08 19:32 · ziya · Roles: Ziya = Masumi payments + buyer orchestrator; Murad = sellers (Apify research, ElevenLabs voice); Mais = dashboard + video. Why: Ziya set up Masumi; team strengths are backend + frontend.
- 2026-10-08 19:32 · ziya · Sellers expose Masumi MIP-003 HTTP (FastAPI), buyer calls them over HTTP. Why: native Masumi standard; in-process calls would make "agents hiring agents" look fake.
- 2026-10-08 19:32 · ziya · Masumi payment service is hosted (Railway), not local Docker. Why: all 3 laptops can reach it; no dependency on one laptop staying awake.
- 2026-10-08 19:32 · ziya · Cut order if behind at 01:00: drop voice seller first. Why: research seller alone still gives a full E2E loop.
- 2026-10-08 19:40 · ziya · Buyer streams live events to dashboard via SSE `GET /events` (JSON: quote, escrow_locked, delivered, verified, released, refunded, blocked, needs_approval). Why: one-way, proxy-friendly, trivial in FastAPI + EventSource.
- 2026-10-08 19:40 · ziya · Demo task = "Brief me on competitor X, voice summary, budget 20 ADA" (research seller + voice seller). Why: matches TOPICS.md demo, uses all 4 partners.
- 2026-10-08 19:40 · ziya · Verifier = hard schema checks first (non-empty, has sources, audio URL plays), then LLM judge vs brief; fail = refund. Why: cheap checks catch obvious junk; LLM judge weakness listed under honest limitations.
- 2026-10-08 19:45 · ziya · Firewall: task budget 20 tADA, hard cap 12 per job, quotes >8 pause for human approval. Why: research (~5) auto-passes, voice (~9) triggers approval, so one run shows both.
- 2026-10-08 19:45 · ziya · Human approves on the dashboard; button calls buyer `POST /approvals/{id}`. Why: visible in video; terminal prompt looks bad.
- 2026-10-08 19:45 · ziya · Refund demo = seller env `BAD_MODE=1` returns junk, verifier fails it, escrow refunds; labelled as a staged failure in the video. Why: reliable refund path, honest labelling.
- 2026-10-08 19:45 · ziya · Wallets: one buyer purchasing wallet (Preprod faucet), each seller registered as its own Masumi agent with its own selling wallet. Why: per-seller payouts visible.
- 2026-10-08 19:50 · ziya · Dashboard = Vite + React single page; reads buyer SSE, submits tasks via buyer `POST /tasks`, approves via `POST /approvals/{id}`. Why: fast reload, looks good on video, whole flow visible.
- 2026-10-08 19:50 · ziya · Checkpoints: 21:30 contracts filled + skeletons answer HTTP; 01:00 full E2E (SIMULATED ok, cut voice if behind); 04:00 feature freeze, video starts; 06:30 video done, repo public; submit by 07:14. Why: leaves 6h for polish and video.
