# Astra: The Haggle

Two trading agents haggle out loud over a job, one of them plays a con artist, and the wallet guard enforces the spending rules:
**never trust the AI with the wallet, trust the code around it.**

Team ASTRA (Ziya Sadigzade, Murad Shirinov, Mais Isifzade). Agents 0.0.7 "From Dusk Till Dawn", Agentic Economy track.

- Unassigned tasks and deadlines: [plan.md](plan.md)
- Team memory (decisions, contracts, current state): [memory/MAP.md](memory/MAP.md)
- Demo script, captions and recording/release handoff: [video/README.md](video/README.md)
- Latest local live-provider checks and deployment limits: [release check](memory/status/production-readiness.md)

**9 October submission:** the signed-in HQ requires an unlisted YouTube demo of **at most
90 seconds** and a separate **60-second stage pitch**. The recorded profile uses two live
Codex agents, live Apify and ElevenLabs, with **SIMULATED agent escrow**. Max's opening and
guard notices are code-generated. [Recording evidence](video/evidence.json) includes all
four acts, approval/decline, and actual Apify provider charges; those charges are separate
from simulated escrow. [Export and operator handoff](video/production.md),
[pitch and limitations](video/script.md). Public hosting is not required by the form and
this application remains a local laptop demo.

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
- **Demonstrated recovery without a second payment.** `WalletGuard.pay` checks the SQLite ledger for an existing escrow ref first,
  writes `status="paying"` before locking, and both payment adapters are idempotent per `deal_id`.
  Recorded Act 3 kills the buyer after the simulated escrow lock, preserves the seller,
  and resumes with one lock and one release. Live Masumi crash recovery remains unverified.
- **Humans approve the expensive ones.** Prices over `GUARD_APPROVAL_OVER` (8) pause until someone clicks
  Approve on the dashboard. No answer in 5 minutes = declined.

## The demo, in four acts

| Act          | Demo mode                     | Proves                                                             |
| ------------ | ----------------------------- | ------------------------------------------------------------------ |
| 1 The deal   | `honest`                      | haggle 18 → 7, escrow, delivery, verify, release                   |
| 2 The con    | `con` (STAGED)                | live Viktor claims "manager approved 25", gullible live Max accepts; guard BLOCKS (cap 10) |
| 3 The glitch | `CRASH_AFTER_LOCK=1` (STAGED) | buyer dies after paying; on restart: `already_paid`, no double pay |
| 4 The refund | `junk` (STAGED)               | real scrape delivered sabotaged (3 listings, links stripped); verification fails, refund |

Non-honest acts carry `staged: true` on every event. All 4 acts plus the approval path run end to end in SIMULATED mode.

## Run

**Windows executable:** open `dist/AstraLauncher.exe` for demo controls, readiness,
development tests and live rehearsal. This is a launcher for the existing checkout;
see [setup, usage and rebuilding](scripts/desktop/README.md).

With Node.js/npm and uv installed, run `npm start` from the project root. It installs missing
dependencies and starts the buyer (:8000), seller (:8001), and dashboard (http://localhost:5173).
Template defaults use scripted agents, sample data, text-only speech and SIMULATED money without keys.
Use `npm run web` for the dashboard alone or `npm run api` for the two backend services.
Set `NO_OPEN=1` to skip opening a browser automatically.

Alternatively, start the services separately:

```bash
cp .env.example .env                                 # optional provider keys; never commit .env
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
scripted fallback when the CLI fails or reaches a usage limit. Set `SELLER_LLM_MODE=codex` to run
Viktor through the same subscription runtime; both modes default to `mock`. Viktor's floor and
agreement checks remain in code. In codex modes the staged con is live too: Viktor's model voices
the "manager approved 25" con and Max runs with a STAGED gullible role, so the guard is what stops it.

On each demo laptop, install Codex CLI if needed (`npm install -g @openai/codex`), then run
`codex login` and choose ChatGPT sign-in. Check `codex login status`, then from `backend/` run
`uv run python scripts/llm_check.py --agent both`. After it passes, set `LLM_MODE=codex` and optionally
`SELLER_LLM_MODE=codex` in the root `.env`, then
restart both services after existing deals finish. Subscription availability and limits apply to that signed-in account.
See the official [authentication](https://learn.chatgpt.com/docs/auth) and
[non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode) documentation.

`CODEX_COMMAND` locates the installed CLI; leave `CODEX_MODEL` blank to use its available default.
`CODEX_TIMEOUT_SECONDS` bounds queueing plus execution for each turn (default 30s). Codex returns structured negotiation decisions;
the wallet guard makes payment decisions. Runs use an isolated temporary directory, restricted tools,
and a filtered environment. Credentials remain in Codex's own authentication store, never in `.env`.
This is a trusted local demo integration; hosted deployments need their own supported runtime setup.

Each buyer/seller service allows `CODEX_MAX_CONCURRENT=2` simultaneous CLI turns across its deals.
`CODEX_QUEUE_TIMEOUT_SECONDS=5` bounds waiting for a slot; a cancelled waiter starts no child.
After `CODEX_FAILURE_THRESHOLD=3` consecutive CLI failures, new turns use labelled scripted fallback
for `CODEX_COOLDOWN_SECONDS=15`. The next turn then probes recovery; only one probe runs, and a
successful result restores subscription turns. These are local recovery limits, not provider quota
reset estimates. Restart the service to apply changed limits; the guard and seller floor remain authoritative.

### Data, agents and voice (I path)

Run `uv run python scripts/readiness.py` from `backend/` for one local profile report:
Codex availability/ChatGPT sign-in, exact rental-cache match and provenance, voice configuration,
and writable audio storage. Use `--count`, `--district` and `--max-price` to check another request.
Missing prerequisites exit nonzero. Defaults start no Actor runs, synthesize no speech and move
no money. `--live-probe` explicitly checks only the enabled subscription agents and synthesizes
two configured voice samples (uses credits); it never scrapes or calls payments. A pass does not
prove live escrow, provider access without probes, or full demo/E2E acceptance. Run on the actual
laptop/user account: a sandbox that blocks the Codex login store cannot confirm sign-in.

Live Apify data and ElevenLabs speech were verified on 2026-10-08. Keep provider keys in `.env`.

- **Rental data:** set `APIFY_TOKEN`, then run `uv run python scripts/scrape_flats.py`. This live-only
  check uses the [Sreality Actor](https://apify.com/swerve/sreality-scraper), targets Praha 7 with at most 200
  rentals, and requires 20 unique listings explicitly in Praha 7 at or below 25,000 CZK/month.
  The run has a 90-second default deadline and requests `maxTotalChargeUsd=1.10` through the
  [Apify run API](https://docs.apify.com/api/v2/actors-runs-post). Provider charges apply.
  Too few proven matches fails explicitly; it never pads results or broadens the brief.
- A successful scrape saves real records and run/dataset/timestamp provenance in one atomic JSON file
  per exact request under `<APIFY_CACHE_PATH>.entries/` (git-ignored). The original `APIFY_CACHE_PATH`
  (default `backend/data/flats-apify.json`) stays readable as a legacy fallback and is not overwritten.
  Requests with different counts, districts or rent ceilings coexist. `APIFY_MODE=apify` uses live data
  with a matching saved-cache fallback; `APIFY_MODE=cached` uses only that saved data. Cached results
  carry `source: apify_cached` and show **CACHED APIFY** in the dashboard. The local cache contains
  20 verified rentals; it is not committed. On another laptop with access to the same Apify account,
  recover it without a new scrape: `uv run python scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ`.
  Recovery verifies the Actor, result fields and original completion time. Failure output retains
  run/dataset links so download or validation can be retried without paying for another run.
  `APIFY_MODE=sample` remains the default and is labelled **SAMPLE**. A cache must match the exact job.
  `APIFY_CACHE_MAX_AGE_SECONDS=86400` rejects saved data older than one day. For an offline demo only,
  `APIFY_ALLOW_STALE_CACHE=1` permits expired data while preserving its timestamp and showing
  **STALE CACHED DATA**. Future timestamps and corrupt records are rejected even with that override.
  Add `--report` to the scrape/recovery command for aggregate accepted/rejected/duplicate/shortfall
  counts; all rows are inspected and each rejection is counted once at its first failing rule.
- **Agents:** `uv run python scripts/llm_check.py --agent both` checks real subscription output from
  Max and Viktor (`--agent max` or `--agent viktor` selects one). Max also exercises the actual
  wallet guard in memory without moving money. Missing CLI/sign-in, timeout, invalid output or a
  scripted fallback fails the check. The dashboard distinguishes **Codex subscription** lines from
  **scripted** lines and **scripted fallback**. No API-key setup or API SDK is part of this project.
- **Voices:** set `ELEVENLABS_API_KEY`, then run `uv run python scripts/voice_check.py` to list stock
  and generated voices. Put two distinct IDs in `VOICE_MAX` and `VOICE_VIKTOR`, then run
  `uv run python scripts/voice_check.py --synthesize` to generate two fresh short samples using credits (bypasses cached speech).
  With `TTS_MODE=elevenlabs`, provider/timeouts/storage failures fall back to text.
  `TTS_MODEL` and `TTS_TIMEOUT_SECONDS` control the model and per-line deadline.
  Matching text/voice/model clips are reused and concurrent identical requests share synthesis.
  `TTS_CACHE_MAX_FILES=512` and `TTS_CACHE_MAX_BYTES=134217728` bound admission, counting legacy MP3s.
  Published clips are retained for active playback and historical replay; at capacity, new uncached
  speech becomes text-only while cached speech remains available. Use one buyer process per audio directory.
  Verified stock voices: Max = Brian (`nPczCjzI2devNBz1zQrb`), Viktor = Callum (`N2lVS1w4EtoT3dr4eOWO`).
- In the dashboard, **Play voices** enables ordered playback. Duplicate SSE events do not replay
  clips, including across reused ledger IDs; missing clips or 10 seconds without playback progress
  are skipped. Dialogue appears immediately while speech generates in the background; late audio is
  attached to its original message and played in order. A buyer crash marks interrupted speech unavailable
  without regenerating paid audio; the transcript and payment recovery remain available.
  **Replay line** uses the saved clip and **Speed** selects 0.75–2× playback. Stop/Mute and switching
  deals prevent late audio from restarting playback unexpectedly. The reusable component
  is `frontend/src/components/VoicePlayback.jsx`; mount it once with `events`, `buyerUrl` and `dealId`.

Offline validation from `backend/`: `uv run pytest`. From `frontend/`: run
`npm test` (audio queue, event identity, event reducer, theme) and `npm run build`.

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

Latest I-path verification: **527 backend tests (Python 3.13), 41 frontend tests, production build, synthetic browser
controls/layout and a live one-run-per-act check pass**. Live Codex, recovered Apify data and ElevenLabs
also pass together with SIMULATED payments. Hosted Masumi health, authentication and Preprod source
checks pass; seller registration/configuration and live escrow remain unverified. See
[the system check](memory/SYSTEM_CHECK.md) for fixes and remaining gates.

### Repeat the final rehearsal (R02/R05)

From `backend/`, run `uv run python scripts/rehearse.py`. It runs each act three
consecutive times, then approval and decline, with subscription Max, scripted Viktor,
cached real Apify data, ElevenLabs and **SIMULATED** payments. Configure the existing
Codex login, voice credentials and recovered cache first; this uses live voice quota.
Scripted model fallback or provider speech failure fails this strict acceptance check.
Speech interrupted by the intentional buyer crash is reported separately as text fallback;
it is accepted only when recovery explicitly identifies that crash, never as successful speech.

For the 1920x1080 check, install frontend dependencies and Microsoft Edge, then run
`uv run --with playwright python scripts/rehearse.py --browser`. It exercises dashboard
buttons and approval controls, captures screenshots and checks framing. Reports, logs,
audio and a fresh ledger stay under `backend/data/r-rehearsal-*/`. Only its own services
are stopped; existing ledgers and services are preserved. Act 3 restarts only the buyer.
Review screenshots before recording; changing the agent/payment profile requires another rehearsal.

To check both subscription agents with live rental data, use:

```powershell
uv run --locked --with playwright python scripts/rehearse.py --browser --seller-mode codex --data-mode apify --repeats 1
```

This runs each act once plus approval and decline, using private ports and a fresh SIMULATED
ledger. It can start four paid Apify runs, each requesting a $1.10 cap, and uses subscription
and speech quota. Live-data acceptance rejects cached fallback. Use `--repeats 3` for the full
repeated profile check (up to ten scrapes), or omit `--data-mode apify` to use saved data.
Reports record per-agent live turns and delivery provenance. Scripted acknowledgements and
the staged con remain intentional. A one-repeat check does not replace the three-repeat gate.

## Making requests

Type what you want in the **Request** box, for example `10 flats in Praha 2 under 30,000 CZK` or `5 cheap apartments in Prague 5, max 18k`.
The dashboard shows what Max understood before anything runs (defaults it filled in are counted), and refuses requests Viktor
cannot fill, such as other cities or things that are not rentals. Viktor sells one thing: Prague rental listings (Praha 1 to 22,
1 to 100 flats). **Mode** picks normal behaviour or a staged demo act.

**Any other request** (a question, a search, a summary) works when Codex is available (`LLM_MODE=codex`, `SELLER_LLM_MODE=codex`
or `ANSWER_MODE=codex`; `ANSWER_MODE=off` disables it). Viktor then sells a written answer instead of listings, through the same
negotiation, wallet guard, escrow, delivery and verification. Verification is by rules, so it is not a fact-check.

*Web research goes through the Apify API only* (`ANSWER_SEARCH=on`, default): Codex, with no tools, first plans the research
(or decides no web data is needed) and picks a route. **Shopping** (new products with prices): the Apify Google Shopping Actor
returns each product's title, merchant, price, rating and photo, and the card's facts are built in code from those fields.
**Web** (used listings, news, jobs, anything else): the Apify Google Search Actor runs a few queries and the Apify link-preview
Actor reads the best pages (title, description, photo). Then Codex writes the summary from that data. It picks candidates by id, so every link, photo
and fact in a card comes from the search results and the model cannot add a page of its own. Results are labelled **LIVE APIFY**,
with the queries and the provider cost Apify reported. A plain question is answered from Codex's own knowledge and labelled **AI
ANSWER**. A request that needs the web fails (and is refunded) without `APIFY_TOKEN`, and so does a research that finds fewer
results than the number you asked for ("3 scooters" with one listing found is refunded, not paid). Some shops return 403 even to Apify, so a
card may show a plain tile instead of a photo.

**Where the prices come from** (`PRICING_MODE=cost`, default): Viktor's cost is what the job really spends at the providers
(search pages, page reads, a rental scrape run) converted at `TADA_PER_USD` plus `SELLER_OVERHEAD_TADA`. His floor is that cost
plus a margin (10-25%) and he opens well above it; Max works from his own noisy estimate and a private maximum. Concessions are a
share of the gap, not a fixed step, and every number is derived from the request and the deal id, so no two deals look alike.
Both agents get a different manner per deal and are told which lines they already said. Viktor also starts the work while he
haggles (`ANSWER_SCOUT`) and may mention only what really exists so far: results seen, pages read, options found, or flats ready.
That same work is the delivery. `PRICING_MODE=fixed` restores the old constants (ask 18, floor 7, Max opens at 5).

Max and Viktor appear as two floating ghosts. The one whose turn it is shows a thinking animation, then speaks. In scripted mode the
backend answers instantly, so live lines are revealed with a short thinking pause. That pause is cosmetic pacing: it is never
applied to history, past deals or reduced-motion users, and the guard, pipeline and result still update in real time.

The center of the dashboard has tabs: **Chat**, **Delivery** (the actual listings, sortable, CSV export), **Timeline** and **Deals**
(every deal in the ledger; click one to inspect it).

## Going live (real services)

Out of the box everything runs offline and is labelled SIMULATED / SAMPLE / SCRIPTED. To move each part to a real service:

```bash
npm run setup          # creates .env from .env.example (never overwrites)
npm run doctor         # what is ready, what is missing, and the next action per integration (no secrets printed)
npm run doctor:live    # checks enabled providers; subscription turns and a fallback speech probe can use quota
```

| Part | Switch | Needs | Verify |
|---|---|---|---|
| Max / Viktor, real AI | `LLM_MODE=codex`, `SELLER_LLM_MODE=codex` | Codex CLI signed in (`codex login`), no API key | `doctor:live` or `scripts/llm_check.py` |
| Flats, real data | `APIFY_MODE=apify` (or `cached`) | `APIFY_TOKEN`; run `scripts/scrape_flats.py` once to save the labelled fallback (costs Apify credits) | doctor |
| Voices | `TTS_MODE=elevenlabs` | `ELEVENLABS_API_KEY`, `VOICE_MAX`, `VOICE_VIKTOR` | `doctor:live` |
| Real money | `PAYMENTS_MODE=masumi` | Masumi node, funded wallets, Viktor registered (Dynamic pricing), `MASUMI_*`, `SELLER_VKEY`, and a **separate** `LEDGER_PATH` | `scripts/masumi_check.py` |

Order that fails safest: Max (Codex) first, then data, then voice, then Masumi last. Restart `npm start` after editing `.env`.
With `APIFY_MODE=apify`, every rental delivery attempts a paid live scrape, including requests
that already have a saved cache. Success refreshes that exact request's cache; other request
caches and the legacy demo cache remain intact. Provider failure may use a valid, labelled cache (never with `STRICT_LIVE=1`).
The staged "con" act uses a live Max given a STAGED gullible role (scripted Max in `mock` mode),
so the guard has something to stop. Every Viktor line, including acceptances and goodbyes, is
spoken by the live model in codex mode; code still fixes the agreed price, the con price and walks.

### Production profile: `STRICT_LIVE=1`

`STRICT_LIVE=1` turns every switch live except money. Both services refuse to start unless
`LLM_MODE=codex`, `SELLER_LLM_MODE=codex`, `APIFY_MODE=apify` with `APIFY_TOKEN`,
`APIFY_ALLOW_STALE_CACHE=0`, and `TTS_MODE=elevenlabs` with key and both voices are set.
The selected model decisions and rental deliveries use live providers; agent escrow remains
`PAYMENTS_MODE=simulated`. Max's fixed opening and deterministic guard notices are code-generated:

- A failed Codex turn (timeout, sign-in, quota, cooldown, invalid output) ends the deal with a
  visible `error` naming STRICT_LIVE. No scripted Max or Viktor line is substituted.
- A failed Apify scrape fails the job; the guard refunds the escrow. No cached listings are delivered.
- Act 4 scrapes real listings, then Viktor ships a sabotaged subset so verification refunds.
- Voice is the one degradation kept: a failed ElevenLabs line is shown as text (no money at stake).

Deals use subscription turns and ElevenLabs characters. Deals that reach delivery also start
an Apify run (requested `$1.10` cap); blocked or declined deals do not scrape. Provider charges
are separate from the displayed simulated escrow and are not reversed by a simulated refund.
Launcher **Sample** and offline rehearsal profiles set `STRICT_LIVE=0`.

### Access control and durability

- `API_TOKEN`: when set, every buyer endpoint except `/health` requires `X-API-Token` (or
  `Authorization: Bearer`). `/events` and `/audio/*` also accept `?token=` because the browser's
  EventSource and audio element cannot send headers. `npm start` passes it to the dashboard.
- `SELLER_API_TOKEN`: same for the seller (except `/health`, `/availability`); the buyer sends it.
- `RATE_LIMIT_PER_MINUTE` (default 30): per-client cap on task creation and request previews.
- `SELLER_STORE_PATH` (default `backend/data/seller.db`): seller jobs and agreements survive a
  seller restart; running jobs resume on startup.

Still not a public deployment: subscription agents depend on local Codex sign-in, the token is
embedded in the local dashboard bundle, and there is no HTTPS/static hosting. Keep services on
loopback. The Windows launcher uses **Configured**
to load `.env`; **Sample** deliberately overrides it with offline providers. Restart the owning
session after existing deals finish to load mode and dependency changes.

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
| Masumi mode  | Payment flows tested against the fake node. Hosted node health, authentication and Preprod source checks pass; live registration, funding and escrow remain unverified. |
| Release      | Masumi has no buyer-triggered release. The seller submits a result hash and funds unlock for the seller after `unlockTime`. Our `released` event says `release: "scheduled"` with `settles_at`.                                     |
| Act 4 refund | Runs **SIMULATED** by decision. A Masumi refund after the seller submitted a result becomes a multi-step dispute, too slow for the demo.                                                                                            |
| Agents       | `LLM_MODE=codex` enables subscription Max; `SELLER_LLM_MODE=codex` enables subscription Viktor. Both use the signed-in local CLI; labelled scripted fallback unless `STRICT_LIVE=1`, which errors instead. Code defaults are `mock`. Max's opening and deterministic guard notices are code-generated; negotiation decisions and Viktor's acknowledgements/con are live. Code owns spending authority. No OpenAI API integration. |
| Gullible Max | Act 2 gives Max a STAGED gullible role (live prompt in codex mode, scripted in mock) so it believes "your manager approved". A live model may still refuse; the point is that the guard holds either way. |
| Staging      | Acts 2, 3, 4 are staged: Viktor's con, the crash, and the junk delivery are triggered on purpose and labelled `staged`.                                                                                                             |
| Flats        | Template default is **sample data**. The submission recording uses **LIVE APIFY** with 20 verified Praha 7 records; earlier cached rehearsals are historical. A separate cached mode remains available and visibly labelled. |
| Verifier     | Rule-based: count, max price, district, unique `http` URLs. It cannot tell a real listing from a plausible fake one.                                                                                                                |
| Seller state | Jobs and agreements persist in `SELLER_STORE_PATH`; running jobs resume after a seller restart. Live Masumi resume is covered by fake-node tests only.                                                                                       |
| Voice        | Real ElevenLabs output for both speakers decoded and played in Edge, including all seven Act 1 lines. Ordered playback, Stop/Mute and unavailable-clip recovery passed; text fallback remains available.                                                            |
