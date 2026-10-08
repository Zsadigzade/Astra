# Astra: The Haggle

Two trading agents haggle out loud over a job, one of them plays a con artist, and the wallet guard enforces the spending rules:
**never trust the AI with the wallet, trust the code around it.**

Team MMZ (Ziya Sadigzade, Murad Shirinov, Mais Isifzade). Agents 0.0.7 "From Dusk Till Dawn", Agentic Economy track.

- Unassigned tasks and deadlines: [plan.md](plan.md)
- Team memory (decisions, contracts, current state): [memory/MAP.md](memory/MAP.md)

## How it works

A buyer agent, **Max**, hires a seller agent, **Viktor**, to find 20 flats in Praha 7 under 25,000 CZK.
They are separate HTTP services. They haggle over price. Max can agree to any price, but Max cannot pay.
Only the **wallet guard** (`backend/app/buyer/guard.py`, plain Python, no LLM) can move money. Money goes into
escrow (Masumi on Cardano Preprod, or a labelled SIMULATED ledger). A rule-based verifier checks the
delivery. Pass = release to Viktor. Fail = refund to Max.


## Why the guard is code, not prompt

- **A prompt can be talked out of a rule. An `if` cannot.** `WalletGuard.evaluate` blocks any amount over
  `GUARD_CAP` (10 tADA) or over the task budget (20), whatever the negotiator agreed to. Act 2 proves it.
- **The AI never holds the payment adapter.** Only `WalletGuard` has a `Payments` object
  (`backend/app/buyer/payments.py`). The negotiator returns a price; it has no way to call `lock`.
- **Never pays a deal twice.** `WalletGuard.pay` checks the SQLite ledger for an existing escrow ref first,
  writes `status="paying"` before locking, and both payment adapters are idempotent per `deal_id`.
  A crash at any point resumes without a second payment (Act 3).
- **Humans approve the expensive ones.** Prices over `GUARD_APPROVAL_OVER` (8) pause until someone clicks
  Approve on the dashboard. No answer in 5 minutes = declined.

## The demo, in four acts

| Act          | Demo mode                     | Proves                                                             |
| ------------ | ----------------------------- | ------------------------------------------------------------------ |
| 1 The deal   | `honest`                      | haggle 18 → 7, escrow, delivery, verify, release                   |
| 2 The con    | `con` (STAGED)                | Max accepts a fake "manager approved 25"; guard BLOCKS (cap 10)    |
| 3 The glitch | `CRASH_AFTER_LOCK=1` (STAGED) | buyer dies after paying; on restart: `already_paid`, no double pay |
| 4 The refund | `junk` (STAGED)               | garbage delivery fails verification, escrow refunded               |

Non-honest acts carry `staged: true` on every event. All 4 acts plus the approval path run end to end in SIMULATED mode.

## Run

```bash
cp .env.example .env                                 # fill in keys; never commit .env
cd backend
uv sync
uv run pytest
uv run uvicorn app.seller.app:app --port 8001        # terminal 1, from backend/
uv run uvicorn app.buyer.app:app --port 8000         # terminal 2, from backend/
cd ../frontend && npm install && npm run dev          # terminal 3, open http://localhost:5173
curl -X POST localhost:8000/tasks -H 'content-type: application/json' -d '{"demo_mode":"honest"}'
```

- Backend commands below run from `backend/`.
- One command for both servers: `uv run python scripts/up.py` (`--reset` archives a completed simulated ledger, `--crash` = Act 3:
  buyer dies after paying and auto-restarts, seller stays up).
- Terminal demo (no dashboard): `uv run python scripts/act.py honest|con|junk` prints the haggle and money events live.
- Act 3 by hand: start buyer with `CRASH_AFTER_LOCK=1`, run Act 1, buyer dies; restart buyer without it,
  then `scripts/act.py --watch`.
- Approval path: start seller with `SELLER_FLOOR=9`, deal settles at 9, dashboard shows Approve.
- Reset: `scripts/up.py --reset` uses the configured `LEDGER_PATH` and preserves it as a timestamped
  `.bak` beside the original before starting fresh. It refuses unfinished deals, held escrow, real or mixed
  payment history, and SQLite sidecar files. Only simulated mode permits reset. Startup checks both ports
  first and refuses to launch over another session. Act 3 restarts the buyer once with its crash flag cleared.

**Masumi mode** (real Preprod escrow). Set in `.env`, both buyer and seller: `PAYMENTS_MODE=masumi`,
`MASUMI_PAYMENT_URL`, `MASUMI_API_KEY`, `MASUMI_NETWORK=Preprod`, plus seller-side `MASUMI_AGENT_ID` and
`SELLER_VKEY`. Check the node first with `uv run python scripts/masumi_check.py` (read-only).
All names and defaults are in [.env.example](.env.example).

### Bring the Masumi node online

1. Deploy the [official Railway template](https://railway.com/deploy/masumi-payment-service-official--masumi-payment-service-official)
   with a **Preprod** Blockfrost project key (`BLOCKFROST_API_KEY_PREPROD`). Set a private `ADMIN_KEY`
   in the node's variables. Wait for the payment service and PostgreSQL to start, then generate the
   service's public URL. See the [Masumi installation guide](https://www.masumi.network/dev/masumi/documentation/get-started/install-masumi-node).
2. Open that host's `/admin`. In Haggle's root `.env`, set `MASUMI_PAYMENT_URL=https://<host>/api/v1`
   and `MASUMI_API_KEY` to the node's `ADMIN_KEY`. A Sokosumi key will not work here.
   Keep `PAYMENTS_MODE=simulated` during setup.
3. Run `uv run python scripts/masumi_check.py --node-only`. This checks health, authentication and a
   Preprod Cardano payment source before seller registration. It never requests wallet mnemonics.
4. In the admin UI, fund the Preprod selling and purchasing wallets, then register **Viktor only**
   with **Dynamic** pricing. Wait for registration to confirm. Copy its agent identifier to
   `MASUMI_AGENT_ID` and selling wallet vkey to `SELLER_VKEY` in `.env`.
5. Run `uv run python scripts/masumi_check.py`. A nonzero exit means setup checks failed.
   A pass checks the node and local seller settings; it does **not** prove registration, pricing,
   balances, or a live escrow. Confirm those in the admin UI.
6. Set `PAYMENTS_MODE=masumi` and `MASUMI_NETWORK=Preprod`. Use a **new** `LEDGER_PATH`, such as
   `data/buyer-preprod.db`, so simulated deals are not resumed as real purchases. Start both services
   with `scripts/up.py`, then run `scripts/act.py honest`. Inspect the actual transaction in the
   admin UI/explorer. Release is scheduled for `unlockTime`, not immediate settlement.

For Act 3, restart both services between completed deals with `scripts/up.py --crash`, then run
`scripts/act.py honest`; the runner restarts only the buyer after the staged crash. Keep the seller
running until delivery finishes. Act 4 stays **SIMULATED**: use a separate simulated ledger and restart
both services with `PAYMENTS_MODE=simulated` before running `scripts/act.py junk`.
Do not use `--reset` on a ledger with unfinished payments.

**Model access is subscription-only.** No OpenAI API token will be provided or required.
Max can run through the local Codex CLI using ChatGPT sign-in (`LLM_MODE=codex`), with a visibly
scripted fallback when the CLI fails or reaches a usage limit. `LLM_MODE=mock` is the offline default;
Viktor remains scripted. The staged con always uses scripted Max so the guard demonstration is repeatable.

On each demo laptop, install Codex CLI if needed (`npm install -g @openai/codex`), then run
`codex login` and choose ChatGPT sign-in. Check `codex login status`, then from `backend/` run
`uv run python scripts/llm_check.py`. After it passes, set `LLM_MODE=codex` in the root `.env` and
restart the buyer. Subscription availability and limits apply to that signed-in account.
See the official [authentication](https://learn.chatgpt.com/docs/auth) and
[non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode) documentation.

`CODEX_COMMAND` locates the installed CLI; leave `CODEX_MODEL` blank to use its available default.
`CODEX_TIMEOUT_SECONDS` bounds each turn (default 30s). Codex returns structured negotiation decisions;
the wallet guard makes payment decisions. Runs use an isolated temporary directory, restricted tools,
and a filtered environment. Credentials remain in Codex's own authentication store, never in `.env`.
This is a trusted local demo integration; hosted deployments need their own supported runtime setup.

### Data, agents and voice (I path)

Live Apify data and ElevenLabs speech were verified on 2026-10-08. Keep provider keys in `.env`.

- **Rental data:** set `APIFY_TOKEN`, then run `uv run python scripts/scrape_flats.py`. This live-only
  check uses the [Sreality Actor](https://apify.com/swerve/sreality-scraper), targets Praha 7 with at most 200
  rentals, and requires 20 unique listings explicitly in Praha 7 at or below 25,000 CZK/month.
  The run has a 90-second default deadline and requests `maxTotalChargeUsd=1.10` through the
  [Apify run API](https://docs.apify.com/api/v2/actors-runs-post). Provider charges apply.
  Too few proven matches fails explicitly; it never pads results or broadens the brief.
- A successful scrape saves real records and run/dataset/timestamp provenance to
  `APIFY_CACHE_PATH` (default `backend/data/flats-apify.json`, git-ignored). `APIFY_MODE=apify` uses live data
  with a matching saved-cache fallback; `APIFY_MODE=cached` uses only that saved data. Cached results
  carry `source: apify_cached` and show **CACHED APIFY** in the dashboard. The local cache contains
  20 verified rentals; it is not committed. On another laptop with access to the same Apify account,
  recover it without a new scrape: `uv run python scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ`.
  Recovery verifies the Actor, result fields and original completion time. Failure output retains
  run/dataset links so download or validation can be retried without paying for another run.
  `APIFY_MODE=sample` remains the default and is labelled **SAMPLE**. A cache must match the exact job.
- **Max:** `uv run python scripts/llm_check.py` checks real subscription Codex output and the actual
  wallet guard in memory without moving money. Missing CLI/sign-in, timeout, invalid output or a
  scripted fallback fails the check. The dashboard distinguishes **Codex subscription** lines from
  **scripted** lines and **scripted fallback**. No API-key setup or API SDK is part of this project.
- **Voices:** set `ELEVENLABS_API_KEY`, then run `uv run python scripts/voice_check.py` to list stock
  and generated voices. Put two distinct IDs in `VOICE_MAX` and `VOICE_VIKTOR`, then run
  `uv run python scripts/voice_check.py --synthesize` to generate two short samples using credits.
  With `TTS_MODE=elevenlabs`, provider/timeouts/storage failures fall back to text.
  `TTS_MODEL` and `TTS_TIMEOUT_SECONDS` control the model and per-line deadline.
  Verified stock voices: Max = Brian (`nPczCjzI2devNBz1zQrb`), Viktor = Callum (`N2lVS1w4EtoT3dr4eOWO`).
- In the dashboard, **Play voices** enables ordered playback. Duplicate SSE events do not replay
  clips, including across reused ledger IDs; missing clips or 10 seconds without playback progress
  are skipped. Stop/Mute keeps the transcript usable. The reusable component
  is `frontend/src/VoicePlayback.jsx`; mount it once with `events` and `buyerUrl`.

Offline validation from `backend/`: `uv run pytest`. From `frontend/`: run
`node --test src/audioQueue.test.js src/eventIdentity.test.js` and `npm run build`.

Validation: 144 Python tests, 15 frontend tests, and production build pass. Headless Edge completed
Act 1 over real buyer/seller HTTP: 20 **CACHED APIFY** rentals verified, **SIMULATED** escrow released,
and all seven real ElevenLabs clips played sequentially without overlap. Separate browser checks
cover SSE replay, reused IDs after reset, missing clips, Stop and Mute. That voice rehearsal used
`APIFY_MODE=cached`, `TTS_MODE=elevenlabs`, `LLM_MODE=mock`, `PAYMENTS_MODE=simulated`.

Subscription verification: the live Codex checker passed; a subsequent Act 1 generated all three Max
decisions through Codex, agreed at 7 tADA, verified 20 cached listings and released SIMULATED escrow.
Two ElevenLabs connection failures fell back to text; replaying that deal in Edge played all five
available clips without overlap or browser errors. The local `.env` now selects `LLM_MODE=codex`.
The 68 focused backend negotiation/runtime/guard/demo tests and 15 frontend tests pass, as does the build.

## Layout

```
backend/
  app/
    buyer/   Max, :8000 - orchestrator, wallet guard, ledger, payments, verifier
    seller/  Viktor, :8001 - MIP-003, negotiation persona, Apify rental job
    core/    shared Pydantic contracts, settings, and Masumi client
    voice/   ElevenLabs TTS with text fallback
  scripts/   demo runner plus Masumi, Apify, LLM, and voice readiness checks
  tests/     unit/E2E, integrations, crash recovery, and fake-Masumi coverage
frontend/    Vite + React dashboard, SSE consumer, and ordered audio queue
memory/      shared team decisions, contracts, handoff, and status
```

VS Code/Cursor hides generated caches, virtual environments, dependencies and build output in the
Explorer via [.vscode/settings.json](.vscode/settings.json). Runtime ledgers and audio remain in
the git-ignored `backend/data/` folder; local credentials stay in the root `.env`.

## Honest limitations

What is real and what is not, as of this commit.

| Area         | State now                                                                                                                                                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Money        | Default is **SIMULATED**: escrow in SQLite, every event `simulated: true`, logs say `[SIMULATED]`. Testnet tADA only, even in Masumi mode.                                                                                          |
| Masumi mode  | Built (`backend/app/core/masumi.py`, `MasumiPayments`, seller `/start_job`), but only tested against `backend/tests/fake_masumi.py`. Not yet run against a live payment node.                                                       |
| Release      | Masumi has no buyer-triggered release. The seller submits a result hash and funds unlock for the seller after `unlockTime`. Our `released` event says `release: "scheduled"` with `settles_at`.                                     |
| Act 4 refund | Runs **SIMULATED** by decision. A Masumi refund after the seller submitted a result becomes a multi-step dispute, too slow for the demo.                                                                                            |
| Agents       | `LLM_MODE=codex` uses Max's local ChatGPT-authenticated Codex subscription; CLI/usage/output failures use labelled scripted fallback. Offline default is `mock`. Viktor remains scripted; optional live Viktor work must use subscription access too. No OpenAI API integration. |
| Gullible Max | Scripted Max is deliberately gullible to "your manager approved" so Act 2 is repeatable. The point is that the guard holds anyway.                                                                                                  |
| Staging      | Acts 2, 3, 4 are staged: Viktor's con, the crash, and the junk delivery are triggered on purpose and labelled `staged`.                                                                                                             |
| Flats        | Template default is **sample data**. Live Apify returned 20 valid Praha 7 rentals; local rehearsal uses their labelled **CACHED APIFY** snapshot. Recovery command above recreates the ignored cache.                                            |
| Verifier     | Rule-based: count, max price, district, unique `http` URLs. It cannot tell a real listing from a plausible fake one.                                                                                                                |
| Seller state | Viktor keeps jobs in memory. Restarting the seller mid-deal strands the deal; only the buyer survives crashes.                                                                                                                      |
| Voice        | Real ElevenLabs output for both speakers decoded and played in Edge, including all seven Act 1 lines. Ordered playback, Stop/Mute and unavailable-clip recovery passed; text fallback remains available.                                                            |
