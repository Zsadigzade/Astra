# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

## Environment variables
| Name | Used by | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | all agents | OpenAI key |
| `MODEL` | all agents | model id, cheap default |
| `MASUMI_PAYMENT_URL` | payments | hosted Masumi payment service base URL, ends in `/api/v1` |
| `MASUMI_API_KEY` | payments | Masumi admin/API key |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated` |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |
| `BAD_MODE` | seller agents | superseded by task `demo_mode: junk` (2026-10-08 21:40) |
| `LLM_MODE` | buyer, seller | `mock` (scripted, default) or `openai` (TODO) |
| `GUARD_CAP` / `GUARD_APPROVAL_OVER` | buyer | hard cap per deal (10) / approval line (8), tADA |
| `SELLER_URL` | buyer | seller base URL, default `http://localhost:8001` |
| `SELLER_FLOOR` | seller | Viktor's lowest price (7); `9` forces the approval path |
| `APIFY_MODE` | seller | `sample` (canned, labelled) or `apify` (TODO) |
| `TTS_MODE`, `VOICE_MAX`, `VOICE_VIKTOR` | buyer (voice/) | `off`/`elevenlabs` + ElevenLabs voice ids |
| `CRASH_AFTER_LOCK` | buyer | `1` = STAGED Act 3, buyer exits right after escrow lock |
| `LEDGER_PATH` | buyer | SQLite file, default `data/buyer.db` (delete to reset) |

## Components
Source of truth for payloads: `shared/models.py`. Change it = tell the team.

### buyer "Max" (orchestrator + wallet guard + verifier) — owner: ziya
- runs: `uv run uvicorn buyer.app:app --port 8000`
- `POST /tasks` body `TaskCreate` {text, budget, job:{count, district, max_price_czk}, demo_mode: honest|con|junk} → {task_id, deal_id}
- `GET /events` SSE, `data:` = `Event` {id, ts, type, task_id, deal_id, simulated, staged, data}; replays history on connect.
  types: task_created, negotiation{speaker: max|viktor, text, price, action, audio_url}, quote{price}, needs_approval{price, reason},
  approved, blocked{reason}, escrow_locked{ref, price}, already_paid, delivered{items, source, result}, verified{ok, checks},
  released, refunded{failed}, walked_away{reason}, balances{buyer, seller, escrow}, error{message}
- `POST /approvals/{deal_id}` body {approve: bool}; 404 if nothing pending
- `GET /deals`, `GET /balances`, `GET /health`, `GET /audio/<file>.mp3`

### seller "Viktor" (Apify flats) — owner: murad (skeleton by ziya, murad to confirm)
- runs: `uv run uvicorn seller.app:app --port 8001`
- `POST /negotiate` `NegotiateRequest` {deal_id, round, action: open|counter|accept|walk, offer, message, job, demo_mode} → `NegotiateResponse` {deal_id, round, action: counter|accept|walk, price, message}
- MIP-003: `GET /availability`, `GET /input_schema`, `POST /start_job` {identifier_from_purchaser=deal_id, input_data:{deal_id, agreed_price, job, demo_mode}} → {status, job_id, price, blockchainIdentifier?}; idempotent per identifier; 409 if price != agreed. `GET /status?job_id=` → {job_id, status, result:{flats:[{title, price_czk, district, url}], source: sample|apify}}
- MIP-003 field names unverified against Masumi docs.

### voice (TTS for haggle lines) — owner: murad
- module `voice/tts.py`, called by buyer; returns `/audio/<id>.mp3` or None (text fallback). No port (:8002 freed).

### dashboard — owner: mais
- runs: `cd dashboard && npm run dev` (:5173); `VITE_BUYER_URL` overrides buyer URL
- consumes buyer `/events`, `/tasks`, `/approvals/{deal_id}`, `/audio/*`
