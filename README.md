# Astra: The Haggle

Two AI agents haggle out loud over a job, one of them is a con artist, and the wallet still cannot be scammed:
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

Dashboard only, from the project root, one command: `npm start` (installs frontend deps if needed, serves
http://localhost:5173 and opens it). It needs the backend on :8000 to show live data; without it the page
reports the buyer as unreachable.

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
- One command for both servers: `uv run python scripts/up.py` (`--reset` clears `backend/data`, `--crash` = Act 3:
  buyer dies after paying and auto-restarts, seller stays up).
- Terminal demo (no dashboard): `uv run python scripts/act.py honest|con|junk` prints the haggle and money events live.
- Act 3 by hand: start buyer with `CRASH_AFTER_LOCK=1`, run Act 1, buyer dies; restart buyer without it,
  then `scripts/act.py --watch`.
- Approval path: start seller with `SELLER_FLOOR=9`, deal settles at 9, dashboard shows Approve.
- Reset: `scripts/up.py --reset`, or delete `backend/data/buyer.db` from the project root.

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

**LLM mode:** `LLM_MODE=openai` runs Max on the OpenAI Agents SDK (`OPENAI_API_KEY`, `MODEL`). Default is `mock`.

### Data, agents and voice (I path)

The integrations are implemented; live provider checks still require credentials in `.env`.

- **Rental data:** set `APIFY_TOKEN`, then run `uv run python scripts/scrape_flats.py`. This live-only
  check uses the [Sreality Actor](https://apify.com/swerve/sreality-scraper), scans at most 200 Prague
  rentals, and requires 20 unique listings explicitly in Praha 7 at or below 25,000 CZK/month.
  The run has a 90-second default deadline and requests `maxTotalChargeUsd=1.10` through the
  [Apify run API](https://docs.apify.com/api/v2/actors-runs-post). Provider charges apply.
  Too few proven matches fails explicitly; it never pads results or broadens the brief.
- A successful scrape saves real records and run/dataset/timestamp provenance to
  `APIFY_CACHE_PATH` (default `backend/data/flats-apify.json`, git-ignored). `APIFY_MODE=apify` uses live data
  with a matching saved-cache fallback; `APIFY_MODE=cached` uses only that saved data. Cached results
  carry `source: apify_cached` and show **CACHED APIFY** in the dashboard. No real cache ships yet.
  `APIFY_MODE=sample` remains the default and is labelled **SAMPLE**. A cache must match the exact job.
- **Max:** `uv run python scripts/llm_check.py` checks real structured agent output and the actual
  wallet guard in memory without moving money. It fails if the key is absent or Max falls back to
  scripted output. `MODEL` remains configurable. Negotiation events identify scripted fallbacks;
  the dashboard shows them. No OpenAI API key is available yet, so keep `LLM_MODE=mock`.
- **Voices:** set `ELEVENLABS_API_KEY`, then run `uv run python scripts/voice_check.py` to list stock
  and generated voices. Put two distinct IDs in `VOICE_MAX` and `VOICE_VIKTOR`, then run
  `uv run python scripts/voice_check.py --synthesize` to generate two short samples using credits.
  With `TTS_MODE=elevenlabs`, provider/timeouts/storage failures fall back to text.
  `TTS_MODEL` and `TTS_TIMEOUT_SECONDS` control the model and per-line deadline.
- In the dashboard, **Play voices** enables ordered playback. Duplicate SSE events do not replay
  clips; missing clips are skipped; Stop/Mute keeps the transcript usable. The reusable component
  is `frontend/src/VoicePlayback.jsx`; mount it once with `events` and `buyerUrl`.

Offline validation from `backend/`: `uv run pytest`. From `frontend/`: run
`node --test src/*.test.js` and `npm run build`.

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
| Agents       | Max and Viktor are **scripted** by default (`LLM_MODE=mock`). `LLM_MODE=openai` drives Max only; errors use a labelled scripted fallback. No API key is available for live verification. Viktor's optional LLM persona is deferred. |
| Gullible Max | Scripted Max is deliberately gullible to "your manager approved" so Act 2 is repeatable. The point is that the guard holds anyway.                                                                                                  |
| Staging      | Acts 2, 3, 4 are staged: Viktor's con, the crash, and the junk delivery are triggered on purpose and labelled `staged`.                                                                                                             |
| Flats        | Default is **sample data**. Live Apify adapter and labelled real-cache fallback are implemented and mock-tested; no successful live scrape or real cached dataset has been obtained yet.                                            |
| Verifier     | Rule-based: count, max price, district, unique `http` URLs. It cannot tell a real listing from a plausible fake one.                                                                                                                |
| Seller state | Viktor keeps jobs in memory. Restarting the seller mid-deal strands the deal; only the buyer survives crashes.                                                                                                                      |
| Voice        | ElevenLabs TTS and ordered playback are implemented and tested with mocks. Live API generation and browser listening await a key and two voice IDs; text fallback works.                                                            |
