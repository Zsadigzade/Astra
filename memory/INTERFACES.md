# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

Current assignment (2026-10-08 22:25): Ziya owns I01-I06 (data, agents and voice); Mais/Murad
handle the remaining paths. Older component labels describe the original split.

I-path integration notice: JobResult.source adds `apify_cached`; optional `fetched_at`, `actor_id`,
`dataset_id`, `run_id` describe real data provenance. Dashboard should distinguish sample/live/cached.
Negotiation event data may additionally carry `backend` and `fallback_reason` for Max's actual mode.
Existing required fields and event names stay unchanged. Audio queue is isolated in VoicePlayback.jsx.
Subscription migration: `LLM_MODE=codex` replaces the removed API mode. `backend=codex` marks
subscription-generated Max lines; `mock` still marks scripted lines/fallback. Act 2 forces scripted Max.

## Environment variables
| Name | Used by | Meaning |
|---|---|---|
| `MASUMI_PAYMENT_URL` | payments | hosted Masumi payment service base URL, ends in `/api/v1`; ours (2026-10-08 23:04): `https://masumi-payment-service-production-96e0.up.railway.app/api/v1` |
| `MASUMI_API_KEY` | payments | ADMIN_KEY of our Masumi payment node (header `token`) |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated` |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |
| `BAD_MODE` | seller agents | superseded by task `demo_mode: junk` (2026-10-08 21:40) |
| `LLM_MODE` | buyer | `mock` (scripted, default) or `codex` (Max via local ChatGPT subscription; Viktor stays scripted); other modes rejected |
| `CODEX_COMMAND`, `CODEX_MODEL` | buyer | installed Codex CLI path/name; optional model (blank uses CLI default); authenticate with `codex login` |
| `CODEX_TIMEOUT_SECONDS` | buyer | default 30s per local CLI turn; failure produces labelled scripted fallback; no API keys |
| `GUARD_CAP` / `GUARD_APPROVAL_OVER` | buyer | hard cap per deal (10) / approval line (8), tADA |
| `SELLER_URL` | buyer | seller base URL, default `http://localhost:8001` |
| `SELLER_FLOOR` | seller | Viktor's lowest price (7); `9` forces the approval path |
| `APIFY_MODE` | seller | `sample` (canned, labelled), `apify` (live with matching real-cache fallback), or `cached` (saved real data only) |
| `APIFY_ACTOR_ID`, `APIFY_MAX_ITEMS` | seller | supported actor `swerve/sreality-scraper`; at most 200 Praha 7 records, filtered to exact job |
| `APIFY_TIMEOUT_SECONDS`, `APIFY_CACHE_PATH` | seller | default 90s total run deadline; saved real result JSON (default `backend/data/flats-apify.json` from the project root) |
| `TTS_MODE`, `VOICE_MAX`, `VOICE_VIKTOR` | buyer (voice/) | `off`/`elevenlabs` + ElevenLabs voice ids |
| `TTS_MODEL`, `TTS_TIMEOUT_SECONDS` | buyer (voice/) | default `eleven_flash_v2_5`; total per-line deadline 12s, then text fallback |
| `CRASH_AFTER_LOCK` | buyer | `1` = STAGED Act 3, buyer exits right after escrow lock |
| `LEDGER_PATH` | buyer | SQLite file, default `backend/data/buyer.db`; separate files for simulated/real payments. `up.py --reset` only deletes the default file; never reset unfinished payments. |
| `MASUMI_NETWORK`, `MASUMI_AGENT_ID`, `SELLER_VKEY` | seller (masumi mode) | `Preprod`; Viktor's registry agentIdentifier; selling wallet vkey |
| `MASUMI_POLL_SECONDS`, `MASUMI_PAY_BY_MINUTES`, `MASUMI_SUBMIT_MINUTES` | seller | chain polling + payment deadlines |
| `SOKOSUMI_API_KEY` | nobody yet | Sokosumi marketplace key (agents + jobs, no payments); unused before 01:00 |

## Components
Source of truth for payloads: `backend/app/core/models.py`. Change it = tell the team.

### buyer "Max" (orchestrator + wallet guard + verifier) — owner: ziya
- runs from `backend/`: `uv run uvicorn app.buyer.app:app --port 8000`
- `POST /tasks` body `TaskCreate` {text, budget, job:{count, district, max_price_czk}, demo_mode: honest|con|junk} → {task_id, deal_id}
- `GET /events` SSE, `data:` = `Event` {id, ts, type, task_id, deal_id, simulated, staged, data}; replays history on connect.
  types: task_created, negotiation{speaker: max|viktor, text, price, action, audio_url, backend?, fallback_reason?}, quote{price}, needs_approval{price, reason},
  approved, blocked{reason}, escrow_locked{ref, price}, already_paid, delivered{items, source, result}, verified{ok, checks},
  released, refunded{failed}, walked_away{reason}, balances{buyer, seller, escrow}, error{message}
- `POST /approvals/{deal_id}` body {approve: bool}; 404 if nothing pending
- `GET /deals`, `GET /balances` (501 in masumi mode), `GET /health`, `GET /audio/<file>.mp3`
- masumi mode event data: `escrow_locked`/`already_paid` add {on_chain_state, tx_url, next_action}; `released` adds {release: "scheduled", settles_at}
- demo scripts under `backend/scripts/`: `up.py` (both servers), `act.py` (one act in terminal), `masumi_check.py` (read-only node check)
- `masumi_check.py --node-only` checks node health/auth/Preprod source before registration; default also checks local seller settings. Exit 1 on incomplete checks; exit 0 does not verify registration, Dynamic pricing, balances or live escrow. Accepts local or hosted API URLs ending in `/api/v1`.
- rehearse Masumi mode from `backend/` without a node: `uv run uvicorn tests.fake_masumi:create_fake_masumi --factory --port 3001`, then `scripts/up.py` with `PAYMENTS_MODE=masumi MASUMI_PAYMENT_URL=http://localhost:3001 MASUMI_API_KEY=test-key` (+ dummy `MASUMI_AGENT_ID` 57+ chars, `SELLER_VKEY` 56 hex)
- `llm_check.py` requires real subscription Codex Max output (never scripted fallback) and checks the guard in memory; no money moves. `backend` is `codex`, `mock` or `guard`; `fallback_reason` is an exception category, not provider text. Codex keeps its own sign-in credentials; no OpenAI API token or SDK is used.

### seller "Viktor" (Apify flats) — owner: murad (skeleton by ziya, murad to confirm)
- Data adapter now owned by Ziya (I01/I02); seller payment transport remains outside I scope.
- runs from `backend/`: `uv run uvicorn app.seller.app:app --port 8001`
- `POST /negotiate` `NegotiateRequest` {deal_id, round, action: open|counter|accept|walk, offer, message, job, demo_mode} → `NegotiateResponse` {deal_id, round, action: counter|accept|walk, price, message}
- MIP-003: `GET /availability`, `GET /input_schema`, `POST /start_job` {identifier_from_purchaser=deal_id, input_data:{deal_id, agreed_price, job, demo_mode}} → {status, job_id, price, blockchainIdentifier?}; idempotent per identifier; 409 if price != agreed. `GET /status?job_id=` → {job_id, status, result:{flats:[{title, price_czk, district, url}], source: sample|apify|apify_cached, fetched_at?, actor_id?, dataset_id?, run_id?}}
- `scrape_flats.py` performs one live-only bounded scrape and saves a real-data cache. Cache job must match count/district/price exactly; insufficient valid listings fails, never pads samples. `--run-id` retrieves an existing successful run using GET only, verifies Actor identity and preserves completion time; failure output retains safe run/dataset links.
- masumi mode: `/start_job` also returns blockchainIdentifier, payByTime, submitResultTime, unlockTime, externalDisputeUnlockTime, agentIdentifier, sellerVKey, inputHash; status is `awaiting_payment` until funds lock on-chain. `deal_id` = 20 hex chars (Masumi identifierFromPurchaser).
- Masumi calls live in `backend/app/core/masumi.py` (owner: ziya), shapes from masumi-payment-service main 2026-10-06.

### voice (TTS for haggle lines) — owner: ziya (I05/I06)
- module `backend/app/voice/tts.py`, called by buyer; returns `/audio/<id>.mp3` or None (text fallback). No port (:8002 freed).
- `voice_check.py` lists stock/generated voice IDs; `--synthesize` uses credits to generate two configured samples. Missing credentials/fallback gives nonzero exit for synthesis.
- `frontend/src/VoicePlayback.jsx` accepts `{events, buyerUrl}`; mount once without parallel per-line audio players. Explicit Play, ordered clips, replay deduplication by (id, ts, deal_id), Stop/Mute and error skipping. A 10-second inactivity watchdog skips pending/stalled playback; only advancing media time renews it.

### dashboard — owner: mais
- runs: `cd frontend && npm run dev` (:5173); `VITE_BUYER_URL` overrides buyer URL
- consumes buyer `/events`, `/tasks`, `/approvals/{deal_id}`, `/audio/*`
