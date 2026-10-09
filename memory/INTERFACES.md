# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

Current assignment (2026-10-08 22:25): Ziya owns I01-I06 (data, agents and voice); Mais/Murad
handle the remaining paths. Older component labels describe the original split.

I-path integration notice: JobResult.source adds `apify_cached`; optional `fetched_at`, `actor_id`,
`dataset_id`, `run_id` describe real data provenance. Dashboard should distinguish sample/live/cached.
Negotiation event data may additionally carry `backend` and `fallback_reason` for Max's actual mode.
Existing required fields and event names stay unchanged. Audio queue is isolated in components/VoicePlayback.jsx.
I04 integration notice (00:38): optional `SELLER_LLM_MODE=codex` enables subscription Viktor;
default remains `mock`, preserving the current rehearsal profile. Seller negotiation responses
add optional `backend` (default `mock`) and `fallback_reason`; buyer forwards both into SSE.
`/controls` adds `modes.seller_llm`; dashboard counts both speakers' actual model provenance.
STAGED con stays scripted for both agents. No shared .env mode change is needed for acceptance.
Rental `price_czk` is a JSON integer: booleans, strings and floating-point values are rejected
at the seller-response boundary. Verification rejects URL control characters and invalid ports;
malformed typed responses retain funded escrow for recovery instead of authorizing release.
Subscription migration: `LLM_MODE=codex` replaces the removed API mode. `backend=codex` marks
subscription-generated Max lines; `mock` still marks scripted lines/fallback. Act 2 forces scripted Max.

## Environment variables
I07–I12 integration notice: additive JobResult fields `cache_stale` (default false) and
`cache_age_seconds` label an explicit stale-cache override. `load_cache(job, settings)` stays compatible;
`cache_path(job, settings)` locates a keyed entry under `<APIFY_CACHE_PATH>.entries/`; the legacy file
remains read-only fallback. Negotiation text publishes first with `audio_status: pending|unavailable`;
a later `audio_ready` event carries `message_id`, `message_ts`, `audio_status: ready|unavailable`,
`audio_url` and the same task/deal identity. Unavailable speech includes `reason`:
`buyer_restarted`, `buyer_stopped` or `synthesis_unavailable`; ready clips omit it.
Existing embedded audio_url events stay supported.
I13 runtime and I14 readiness belong to the two terminal sessions; their files are not claimed here.

| Name | Used by | Meaning |
|---|---|---|
| `MASUMI_PAYMENT_URL` | payments | hosted Masumi payment service base URL, ends in `/api/v1`; ours (2026-10-08 23:04): `https://masumi-payment-service-production-96e0.up.railway.app/api/v1` |
| `MASUMI_API_KEY` | payments | ADMIN_KEY of our Masumi payment node (header `token`) |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated`; unknown values rejected by the buyer payment factory. Both adapters enforce the ledger's persisted mode before recovery. |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |
| `BAD_MODE` | seller agents | superseded by task `demo_mode: junk` (2026-10-08 21:40) |
| `PRICING_MODE` / `TADA_PER_USD` / `SELLER_OVERHEAD_TADA` | seller / buyer | `cost` (default) or `fixed`. Cost: `app/core/pricing.py` derives Viktor's quote (cost, floor = cost x 1.10-1.25, opening = floor x 1.55-2.15) and Max's plan (fair, opening, reservation <= ceiling, pace, patience) from the job and deal id; prices have cents. Fixed: ask 18 / floor 7 / Max opens at 5 (tests set it). |
| `ANSWER_SCOUT` | seller | `on` (default). The work starts at `/negotiate` open (general; rentals only in cached/sample mode) and is reused as the job result; `walk` cancels it. Viktor's prompt gets `what_you_have_found_so_far` only from real `Progress`/results. |
| `ANSWER_SEARCH` / `APIFY_SEARCH_ACTOR` / `APIFY_PREVIEW_ACTOR` / `RESEARCH_TIMEOUT_SECONDS` | seller | `on`: general requests that need the web run `app/seller/research.py` through Apify (planner -> search Actor -> preview Actor -> grounded write-up). `JobResult` then has `source:"apify"`, `queries`, `cost_usd`, `items[]` = `{title,url,detail,image,site}` (planner picks `kind` shopping or web; shopping items take price/merchant/photo from the Shopping Actor, `APIFY_SHOPPING_ACTOR`; verifier `enough_findings` needs as many items as the request asked for) (urls only from the search, https only). Plain questions: `source:"codex"`. |
| `ANSWER_MODE` | buyer / seller | `auto` (on when either LLM mode is `codex`), `codex` or `off`. Enables general requests: `POST /requests/parse` returns `kind` (`rental`/`general`); a general job is `{kind:"general", prompt}`; `JobResult` then has `kind`, `answer`, `source:"codex"`, empty `flats`; `delivered.items` is 1; verifier keys `has_result, has_answer, reasonable_length, not_a_placeholder`. `/controls` modes expose `answers`. |
| `LLM_MODE` / `SELLER_LLM_MODE` | buyer / seller | independently `mock` (scripted, default) or `codex` (local ChatGPT subscription); other modes rejected. In codex mode Act 2 is live (Viktor voices the con at code-fixed 25; Max gets a STAGED gullible role) and every Viktor acknowledgement is a live line with code-fixed action/price. |
| `CODEX_COMMAND`, `CODEX_MODEL` | buyer / seller | installed Codex CLI path/name; optional model (blank uses CLI default); authenticate with `codex login` |
| `CODEX_TIMEOUT_SECONDS` | buyer / seller | default 30s for queueing plus local CLI execution; failure produces labelled scripted fallback; buyer allows seller deadline plus cleanup before giving up HTTP; no API keys |
| `CODEX_MAX_CONCURRENT`, `CODEX_QUEUE_TIMEOUT_SECONDS` | buyer / seller | default 2 simultaneous turns per service process, 5s queue wait (inside total turn deadline); cancelled/expired waiters start no child; slots remain occupied until child cleanup finishes |
| `CODEX_FAILURE_THRESHOLD`, `CODEX_COOLDOWN_SECONDS` | buyer / seller | default 3 consecutive CLI failures then 15s local cooldown; one subsequent recovery turn probes availability; success restores turns; no quota reset prediction; restart service to change this policy |
| `MAX_ROUNDS` / `POLL_SECONDS` | buyer | negotiation round limit (6; dashboard can lower it at runtime) / seller job status polling interval (1s) |
| `JOB_SECONDS` / `SELLER_OPENING_ASK` / `AUDIO_DIR` | seller / seller / buyer | simulated work time (2s) / Viktor's opening price (18) / generated voice clip directory |
| `CORS_ORIGINS` | buyer | extra browser origins (comma-separated) allowed to call the buyer; any `localhost` / `127.0.0.1` port is always allowed; never `*` |
| `GUARD_CAP` / `GUARD_APPROVAL_OVER` | buyer | hard cap per deal (10) / approval line (8), tADA |
| `SELLER_URL` | buyer | seller base URL, default `http://localhost:8001` |
| `SELLER_FLOOR` | seller | Viktor's lowest price (7); `9` forces the approval path |
| `APIFY_MODE` | seller | `sample` (canned, labelled), `apify` (live with matching real-cache fallback), or `cached` (saved real data only) |
| `APIFY_ACTOR_ID`, `APIFY_MAX_ITEMS` | seller | supported actor `swerve/sreality-scraper`; at most 200 Praha 7 records, filtered to exact job |
| `APIFY_TIMEOUT_SECONDS`, `APIFY_CACHE_PATH` | seller | default 90s total run deadline; legacy cache path and base for per-job `.entries/` directory (default `backend/data/flats-apify.json` from the project root) |
| `APIFY_CACHE_MAX_AGE_SECONDS`, `APIFY_ALLOW_STALE_CACHE` | seller | default 86400s positive finite age limit; override `1` permits stale offline data with original timestamp, age and explicit stale label; never permits corrupt/future-dated data |
| `TTS_MODE`, `VOICE_MAX`, `VOICE_VIKTOR` | buyer (voice/) | `off`/`elevenlabs` + ElevenLabs voice ids |
| `TTS_MODEL`, `TTS_TIMEOUT_SECONDS` | buyer (voice/) | default `eleven_flash_v2_5`; total per-line deadline 12s, then text fallback |
| `TTS_CACHE_MAX_FILES`, `TTS_CACHE_MAX_BYTES` | buyer (voice/) | default 512 files / 134217728 bytes; counts legacy MP3s, retains all published URLs; refuse new unique audio at capacity, reuse existing clips; one buyer per audio directory |
| `STRICT_LIVE` | buyer / seller | `1` = production profile: startup refuses unless codex/codex/apify(+token, no stale override)/elevenlabs(+key, voices); Codex/Apify failures raise (`error` event or refund), never scripted lines or cached listings; voice still degrades to text; payments may stay simulated. Seller returns 503 on a failed live turn. |
| `API_TOKEN` | buyer, dashboard, scripts | when set, all buyer routes except `GET /health` need `X-API-Token` or `Authorization: Bearer`; `/events` and `/audio/*` also accept `?token=`. `npm start` passes it to Vite as `VITE_API_TOKEN` (dev only; never build a production bundle with it). |
| `SELLER_API_TOKEN` | seller, buyer | same for seller routes except `/health` and `/availability`; buyer's seller client sends it |
| `RATE_LIMIT_PER_MINUTE` | buyer | per-client sliding window, separately on `POST /tasks` and `POST /requests/parse`; 429 + `Retry-After`; `0` disables (default 30) |
| `SELLER_STORE_PATH` | seller | SQLite for jobs, start responses and Viktor agreements (default `backend/data/seller.db`); running/awaiting-payment jobs resume on startup in their own payment mode; one file per payment mode |
| `CRASH_AFTER_LOCK` | buyer | `1` = STAGED Act 3, buyer exits right after escrow lock |
| `LEDGER_PATH` | buyer | SQLite file, default `backend/data/buyer.db`; separate files for simulated/real payments. `up.py --reset` archives this configured file to a timestamped `.bak`, only for completed simulated work; refuses unfinished/real/mixed ledgers and SQLite sidecars. Relative paths resolve from `backend/`. |
| `MASUMI_NETWORK`, `MASUMI_AGENT_ID`, `SELLER_VKEY` | seller (masumi mode) | `Preprod`; Viktor's registry agentIdentifier; selling wallet vkey |
| `MASUMI_POLL_SECONDS`, `MASUMI_PAY_BY_MINUTES`, `MASUMI_SUBMIT_MINUTES` | seller | chain polling + payment deadlines |
| `SOKOSUMI_API_KEY` | nobody yet | Sokosumi marketplace key (agents + jobs, no payments); unused before 01:00 |

## Components
Source of truth for payloads: `backend/app/core/models.py`. Change it = tell the team.

Ledger contract (2026-10-08 23:25): the `payments_mode` key in the `ledger_metadata`
key/value table stores the binding. Adapters set it atomically before payment work.
`payment_mode(db)` inspects that binding plus legacy simulated tables, escrow references,
stored start responses and event flags. Opposite/mixed modes, corrupt history and payment
activity without identifiable mode fail closed with `LedgerSafetyError`. The runner reuses
this check for reset, including an empty ledger already bound to Masumi. Keep separate
`LEDGER_PATH` files for each mode; existing deal/event payloads are unchanged.

### buyer "Max" (orchestrator + wallet guard + verifier) — owner: ziya
- runs from `backend/`: `uv run uvicorn app.buyer.app:app --port 8000`
- `POST /requests/parse` body {text} → {ok, summary, job:{count, district, max_price_czk}|null, notes[], examples[]}. Preview only (creates nothing, spends nothing). Deterministic English parser (`backend/app/core/intent.py`): count, `Praha 1`-`Praha 22` (also `Prague N`), rent cap (`under 25,000`, `max 30k`, `up to 18000 CZK`); missing parts get documented defaults and are listed in `notes`; non-rental or non-Prague requests return `ok:false` with a reason. Job bounds on the network: count 1-100, rent 1,000-1,000,000 CZK.
- Conversation order: Max speaks first. The first `negotiation` event of a deal is Max's opening question (`speaker: max`, `action: open`, `price: 0`, `backend: mock`; a fixed template, labelled scripted in every mode, never a model call). Viktor's opening ask follows as his answer.
- `POST /tasks` body `TaskCreate` {text, budget, job:{count, district, max_price_czk}, demo_mode: honest|con|junk} → {task_id, deal_id}
- `GET /events` SSE, `data:` = `Event` {id, ts, type, task_id, deal_id, simulated, staged, data}; replays history on connect.
  types: task_created, negotiation{speaker: max|viktor, text, price, action, audio_url, audio_status?, backend?, fallback_reason?}, audio_ready{message_id, message_ts, audio_status, audio_url, reason?}, quote{price}, needs_approval{price, reason},
  approved, blocked{reason}, escrow_locked{ref, price}, already_paid, delivered{items, source, result}, verified{ok, checks},
  released, refunded{failed}, walked_away{reason}, balances{buyer, seller, escrow}, controls_updated{changed fields}, error{message}
- `POST /approvals/{deal_id}` body {approve: bool}; 404 if nothing pending
- `GET /controls` -> {paused, guard:{cap, approval_over, cap_ceiling}, max_rounds, max_rounds_ceiling, modes:{payments, simulated, llm, seller_llm, tts, model}}.
  `PUT /controls` partial body {paused?, guard_cap?, guard_approval_over?, max_rounds?}; 422 on invalid. Cap may be adjusted within the env `GUARD_CAP` ceiling, approval line never above cap. Runtime only (resets on restart); emits `controls_updated`. While `paused`, `POST /tasks` returns 423; in-flight deals finish.
  Round limits are captured when negotiation starts and used by both the loop and Codex prompt. `modes.model` is the configured Codex model or `Codex default`, or `scripted` in mock mode.
- Task budgets must be positive and finite. Guard checks reject nonfinite money or limits independently. Lost payment replies preserve `paying` intent for idempotent recovery; on restart `WalletGuard.recover` asks the adapter's read-only `find(deal_id, start)` first and records found escrow as `already_paid` before limits are re-checked (unfunded `paying` deals still obey current limits); shutdown cancels owned tasks while retaining persisted approval/payment state.
- Network job requests require count 1–100, rent ceiling 1–1,000,000 CZK and a nonblank district (at most 64 characters); task text is at most 500 characters and budget at most 1,000. Internal JobSpec/Apify adapters still support up to 200 records. Recovery isolates invalid legacy tasks for manual review without changing their records/escrow or preventing other deals from resuming.
- Seller replies must match the requested deal/round and accepted offer. Fresh/stored start acknowledgements must be successful with a nonblank job ID and agreed price; status replies must name the funded job. Failed jobs cannot supply successful results.
- Masumi `released` with `release: scheduled` requires confirmed result submission/release state; otherwise the funded deal stays recoverable. Dashboard keeps scheduled and errored funded amounts in escrow totals, distinct from completed releases.
- `GET /deals`, `GET /balances` (501 in masumi mode), `GET /health`, `GET /audio/<file>.mp3`
- masumi mode event data: `escrow_locked`/`already_paid` add {on_chain_state, tx_url, next_action}; `released` adds {release: "scheduled", settles_at}
- demo scripts under `backend/scripts/`: `up.py` (both servers), `act.py` (one act in terminal), `masumi_check.py` (read-only node check)
- `up.py` checks occupied service ports before reset/launch and child liveness during readiness. Only configured staged crash mode permits one buyer restart, explicitly setting `CRASH_AFTER_LOCK=0`; failed recovery exits nonzero. Cleanup applies only to children this runner launched.
- `masumi_check.py --node-only` checks node health/auth/Preprod source before registration; default also checks local seller settings. Exit 1 on incomplete checks; exit 0 does not verify registration, Dynamic pricing, balances or live escrow. Accepts local or hosted API URLs ending in `/api/v1`.
- rehearse Masumi mode from `backend/` without a node: `uv run uvicorn tests.fake_masumi:create_fake_masumi --factory --port 3001`, then `scripts/up.py` with `PAYMENTS_MODE=masumi MASUMI_PAYMENT_URL=http://localhost:3001 MASUMI_API_KEY=test-key` (+ dummy `MASUMI_AGENT_ID` 57+ chars, `SELLER_VKEY` 56 hex)
- `llm_check.py --agent both` (default) requires real subscription Max and Viktor output; `--agent max|viktor` selects one. Max checks the guard in memory; Viktor checks opening and floor-price acceptance; no money moves. Scripted fallback fails readiness. SSE `backend` is `codex`, `mock` or `guard`; `fallback_reason` is an exception category, not provider text. Codex keeps its own credentials; no OpenAI API token or SDK.

### seller "Viktor" (Apify flats) — owner: murad (skeleton by ziya, murad to confirm)
- Data adapter now owned by Ziya (I01/I02); seller payment transport remains outside I scope.
- runs from `backend/`: `uv run uvicorn app.seller.app:app --port 8001`
- `POST /negotiate` `NegotiateRequest` {deal_id, round, action: open|counter|accept|walk, offer, message, job, demo_mode} → `NegotiateResponse` {deal_id, round, action: counter|accept|walk, price, message, backend: mock|codex, fallback_reason?}. Older responses without provenance default to mock.
- Subscription Viktor serializes turns per deal; exact duplicate rounds replay the same response and stale/conflicting requests return 409. Code enforces the floor, nonincreasing counteroffers and acceptance of the exact eligible buyer offer. Buyer accept/walk acknowledgements remain scripted; malformed model output/timeouts fall back visibly without changing payment authority.
- MIP-003: `GET /availability`, `GET /input_schema`, `POST /start_job` {identifier_from_purchaser=deal_id, input_data:{deal_id, agreed_price, job, demo_mode}} → {status, job_id, price, blockchainIdentifier?}; idempotent per identifier; 409 if price != agreed. `GET /status?job_id=` → {job_id, status, result:{flats:[{title, price_czk, district, url}], source: sample|apify|apify_cached, fetched_at?, actor_id?, dataset_id?, run_id?}}
- `scrape_flats.py` performs one live-only bounded scrape and saves a real-data cache per exact count/district/price job. Atomic entries coexist; legacy single-file caches remain readable. Insufficient valid listings fails, never pads samples. `--run-id` retrieves an existing successful run using GET only, verifies Actor identity and preserves completion time; `--report` prints aggregate validation counts even for insufficient results. Failure output retains safe run/dataset links.
- masumi mode: `/start_job` also returns blockchainIdentifier, payByTime, submitResultTime, unlockTime, externalDisputeUnlockTime, agentIdentifier, sellerVKey, inputHash; status is `awaiting_payment` until funds lock on-chain. `deal_id` = 20 hex chars (Masumi identifierFromPurchaser).
- Masumi calls live in `backend/app/core/masumi.py` (owner: ziya), shapes from masumi-payment-service main 2026-10-06.

### voice (TTS for haggle lines) — owner: ziya (I05/I06)
- module `backend/app/voice/tts.py`, called by buyer; returns `/audio/<id>.mp3` or None (text fallback). No port (:8002 freed).
- `voice_check.py` lists stock/generated voice IDs; `--synthesize` uses credits to generate two fresh configured samples (bypasses TTS cache). Missing credentials/fallback gives nonzero exit for synthesis.
- `frontend/src/components/VoicePlayback.jsx` accepts `{events, buyerUrl, dealId}`; mount once without parallel per-line players. Exact message identity resolves async audio in dialogue order; Play, saved-line Replay, speed 0.75–2x, Stop/Mute and error skipping work through one queue. Deal changes recreate a disabled queue. A 10-second inactivity watchdog skips stalled playback; backend pending speech resolves or fails within twice the per-line timeout (including queue wait).
- Buyer publishes text before TTS, owns up to 64 pending audio tasks and two active syntheses, cancels/drains them on shutdown, and closes unresolved historical audio on restart without paid regeneration. Speech cannot delay payment work.
- TTS validates media type before reading and limits decoded audio to 8 MiB; invalid, oversized, interrupted or timed-out responses use text fallback without publishing partial MP3s.

### dashboard — owner: mais
- also uses `GET|PUT /controls` (launch form, spending limits, pause switch). Frontend state is derived from SSE in `frontend/src/lib/eventReducer.js` (unit-tested).
- runs: `cd frontend && npm run dev` (:5173); `VITE_BUYER_URL` overrides buyer URL
- consumes buyer `/events`, `/tasks`, `/approvals/{deal_id}`, `/audio/*`
