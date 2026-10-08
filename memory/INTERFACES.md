# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

## Environment variables
| Name | Used by | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | all agents | OpenAI key |
| `MODEL` | all agents | model id, cheap default |
| `MASUMI_PAYMENT_URL` | payments | hosted Masumi payment service base URL, ends in `/api/v1` |
| `MASUMI_API_KEY` | payments | ADMIN_KEY of our Masumi payment node (header `token`) |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated` |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |
| `BAD_MODE` | seller agents | superseded by task `demo_mode: junk` (2026-10-08 21:40) |
| `LLM_MODE` | buyer | `mock` (scripted, default) or `openai` (Max on OpenAI Agents SDK; Viktor stays scripted) |
| `GUARD_CAP` / `GUARD_APPROVAL_OVER` | buyer | hard cap per deal (10) / approval line (8), tADA |
| `SELLER_URL` | buyer | seller base URL, default `http://localhost:8001` |
| `SELLER_FLOOR` | seller | Viktor's lowest price (7); `9` forces the approval path |
| `APIFY_MODE` | seller | `sample` (canned, labelled) or `apify` (TODO) |
| `TTS_MODE`, `VOICE_MAX`, `VOICE_VIKTOR` | buyer (voice/) | `off`/`elevenlabs` + ElevenLabs voice ids |
| `CRASH_AFTER_LOCK` | buyer | `1` = STAGED Act 3, buyer exits right after escrow lock |
| `LEDGER_PATH` | buyer | SQLite file, default `data/buyer.db` (delete to reset) |
| `MASUMI_NETWORK`, `MASUMI_AGENT_ID`, `SELLER_VKEY` | seller (masumi mode) | `Preprod`; Viktor's registry agentIdentifier; selling wallet vkey |
| `MASUMI_POLL_SECONDS`, `MASUMI_PAY_BY_MINUTES`, `MASUMI_SUBMIT_MINUTES` | seller | chain polling + payment deadlines |
| `SOKOSUMI_API_KEY` | nobody yet | Sokosumi marketplace key (agents + jobs, no payments); unused before 01:00 |

## Components
Source of truth for payloads: `backend/app/core/models.py`. Change it = tell the team.

### buyer "Max" (orchestrator + wallet guard + verifier) — owner: ziya
- runs from `backend/`: `uv run uvicorn app.buyer.app:app --port 8000`
- `POST /tasks` body `TaskCreate` {text, budget, job:{count, district, max_price_czk}, demo_mode: honest|con|junk} → {task_id, deal_id}
- `GET /events` SSE, `data:` = `Event` {id, ts, type, task_id, deal_id, simulated, staged, data}; replays history on connect.
  types: task_created, negotiation{speaker: max|viktor, text, price, action, audio_url}, quote{price}, needs_approval{price, reason},
  approved, blocked{reason}, escrow_locked{ref, price}, already_paid, delivered{items, source, result}, verified{ok, checks},
  released, refunded{failed}, walked_away{reason}, balances{buyer, seller, escrow}, error{message}
- `POST /approvals/{deal_id}` body {approve: bool}; 404 if nothing pending
- `GET /deals`, `GET /balances` (501 in masumi mode), `GET /health`, `GET /audio/<file>.mp3`
- masumi mode event data: `escrow_locked`/`already_paid` add {on_chain_state, tx_url, next_action}; `released` adds {release: "scheduled", settles_at}
- demo scripts under `backend/scripts/`: `up.py` (both servers), `act.py` (one act in terminal), `masumi_check.py` (read-only node check)
- `masumi_check.py --node-only` checks node health/auth/Preprod source before registration; default also checks local seller settings. Exit 1 on incomplete checks; exit 0 does not verify registration, Dynamic pricing, balances or live escrow. Accepts local or hosted API URLs ending in `/api/v1`.
- rehearse Masumi mode from `backend/` without a node: `uv run uvicorn tests.fake_masumi:create_fake_masumi --factory --port 3001`, then `scripts/up.py` with `PAYMENTS_MODE=masumi MASUMI_PAYMENT_URL=http://localhost:3001 MASUMI_API_KEY=test-key` (+ dummy `MASUMI_AGENT_ID` 57+ chars, `SELLER_VKEY` 56 hex)

### seller "Viktor" (Apify flats) — owner: murad (skeleton by ziya, murad to confirm)
- runs from `backend/`: `uv run uvicorn app.seller.app:app --port 8001`
- `POST /negotiate` `NegotiateRequest` {deal_id, round, action: open|counter|accept|walk, offer, message, job, demo_mode} → `NegotiateResponse` {deal_id, round, action: counter|accept|walk, price, message}
- MIP-003: `GET /availability`, `GET /input_schema`, `POST /start_job` {identifier_from_purchaser=deal_id, input_data:{deal_id, agreed_price, job, demo_mode}} → {status, job_id, price, blockchainIdentifier?}; idempotent per identifier; 409 if price != agreed. `GET /status?job_id=` → {job_id, status, result:{flats:[{title, price_czk, district, url}], source: sample|apify}}
- masumi mode: `/start_job` also returns blockchainIdentifier, payByTime, submitResultTime, unlockTime, externalDisputeUnlockTime, agentIdentifier, sellerVKey, inputHash; status is `awaiting_payment` until funds lock on-chain. `deal_id` = 20 hex chars (Masumi identifierFromPurchaser).
- Masumi calls live in `backend/app/core/masumi.py` (owner: ziya), shapes from masumi-payment-service main 2026-10-06.

### voice (TTS for haggle lines) — owner: murad
- module `backend/app/voice/tts.py`, called by buyer; returns `/audio/<id>.mp3` or None (text fallback). No port (:8002 freed).

### dashboard — owner: mais
- runs: `cd frontend && npm run dev` (:5173); `VITE_BUYER_URL` overrides buyer URL
- consumes buyer `/events`, `/tasks`, `/approvals/{deal_id}`, `/audio/*`
