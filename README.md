# Astra

Team MMZ's project for the Agents 0.0.7 "From Dusk Till Dawn" hackathon, Agentic Economy track.

- **Topic candidates:** [TOPICS.md](TOPICS.md)
- **Working rules for humans and coding agents:** [AGENTS.md](AGENTS.md)
- **Team memory (shared state):** [memory/MAP.md](memory/MAP.md)

## Setup
```bash
cp .env.example .env   # fill in keys; never commit .env
```

## The product: The Haggle
A buyer agent (**Max**) hires a seller agent (**Viktor**) to find 20 flats in Prague 7 under
25,000 CZK. They haggle out loud, money goes into escrow, the delivery is checked, then paid or
refunded. Viktor plays dirty; Max can be fooled; **the wallet guard cannot**. The AI can ask to
pay; only the guard (plain code, `buyer/guard.py`) can pay.

| Act | Demo mode | Proves |
|---|---|---|
| 1 The deal | `honest` | haggle 18 → 7, escrow, delivery, verify, release |
| 2 The con | `con` (STAGED) | Max accepts a fake "manager approved 25"; guard BLOCKS (cap 10) |
| 3 The glitch | `CRASH_AFTER_LOCK=1` (STAGED) | buyer dies after paying; on restart: `already_paid`, no double pay |
| 4 The refund | `junk` (STAGED) | garbage delivery fails verification, escrow refunded |

## Layout
```
shared/     contracts (pydantic) + env settings
buyer/      Max, :8000 - orchestrator, wallet guard, SQLite ledger, payments, verifier   (ziya)
seller/     Viktor, :8001 - MIP-003 + POST /negotiate, persona, flats job              (murad)
voice/      ElevenLabs TTS for haggle lines, text fallback                               (murad)
dashboard/  Vite + React, reads buyer SSE                                                (mais)
tests/      guard unit tests + acts 1, 2, 4 and approval end to end (SIMULATED)
```

## Run
```bash
uv sync
uv run pytest                                        # 11 tests
uv run uvicorn seller.app:app --port 8001            # terminal 1
uv run uvicorn buyer.app:app --port 8000             # terminal 2
cd dashboard && npm install && npm run dev           # terminal 3, open http://localhost:5173
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"demo_mode":"honest"}'
```
Act 3: start buyer with `CRASH_AFTER_LOCK=1`, run Act 1, buyer dies; restart buyer without it.
Approval path: start seller with `SELLER_FLOOR=9`, deal settles at 9, dashboard shows Approve.
Reset: delete `data/buyer.db`.

## Honest limitations (current)
- Money is **SIMULATED** (SQLite escrow) until `MasumiPayments` is built; every event carries `simulated: true`.
- Max and Viktor are **scripted** (`LLM_MODE=mock`); Max is gullible on purpose for Act 2.
- Flats are **sample data** (`source: "sample"`) until the Apify scrape lands.
