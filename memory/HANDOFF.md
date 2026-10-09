# Handoff — integrated main

updated: 2026-10-09 03:11 +02:00 · everything live except payments

## Everything live except payments + hardening (2026-10-09 03:11 +02:00)

- Root `.env` now `STRICT_LIVE=1` with `API_TOKEN`, `SELLER_API_TOKEN`, `RATE_LIMIT_PER_MINUTE=60`
  (values private). Startup refuses any non-live provider; Codex/Apify failures error/refund
  instead of scripted lines or cached listings; voice alone degrades to text. Payments SIMULATED.
- Act 2 con is live (dedicated gullible-Max prompt + live Viktor con line; code fixes 25) and the guard
  blocks. Act 4 junk scrapes live then ships 3 sabotaged listings, refund. All Viktor lines live.
- Auth (header or `?token=` for SSE/audio), per-client rate limit, SQLite seller store
  (`SELLER_STORE_PATH`) with job resume. Launcher EXE rebuilt; Sample profile forces STRICT_LIVE=0.
- Evidence: 575 backend / 54 frontend tests, build; live rehearsal `backend/data/r-rehearsal-965ff982`
  passed all 4 acts + approve/decline (live Apify runs incl. junk, zero fallbacks, 45 clips, 77/23/0).
  First attempt `r-rehearsal-8336dcfa` failed Act 2 (live Max refused the con) — see TRAPS (con prompt entry).
- Services restarted via `npm start` on 8000/8001/5173 with live modes (old up.py + vite session stopped
  with no open deals). Not committed. Still not public hosting (Codex local sign-in, dev token in bundle).

## Local live-provider release check (2026-10-09 02:40 +02:00)

- User selected live data, both agents and voices with SIMULATED payments. Ignored `.env`
  now selects Codex Max/Viktor, live Apify and ElevenLabs; stale override and crash flag off.
- 541 backend tests, 50 frontend tests, production build, dependency audits and six live
  browser scenarios pass. Vite updated to 6.4.4; rehearsal supports live data/both agents
  and uses current dashboard selectors. [Full results and limits](status/production-readiness.md).
- Existing terminal services preserved: restart after current deals finish to load the modes.
  Public hosting is not ready: unauthenticated controls and in-memory seller state remain.
  Deployment destination is unconfirmed. No commit/push/deploy or real payment performed.

## Windows launcher (2026-10-09 02:27, ziya)
- `dist/AstraLauncher.exe` built locally; [usage/build guide](../scripts/desktop/README.md). Uses the checkout and installed dependencies; sample/configured demos, readiness, full development tests and live HTTP rehearsal. Always SIMULATED with isolated ledgers; provider usage explicit. EXE acceptance: 540 backend + 50 frontend tests/build and sample HTTP release/block/refund pass; GUI and owned-process cleanup verified. Existing terminal services preserved. No fresh live-provider acceptance in this packaging task.

## Ghost stage (2026-10-09, samir/claude; uncommitted)
- Chat tab opens with two animated SVG ghosts (`Ghost.jsx`, `GhostStage.jsx`): levitate, blink, thinking (dots, eyes up, sway), speaking (mouth, lean, speech bubble), plus a coin with the price on the table. Pure CSS, no new dependency; all motion off under `prefers-reduced-motion`.
- `hooks/usePacedChat.js` + `lib/pacing.js`: live lines get a thinking beat (~0.7-1.5s) before they appear. COSMETIC pacing: only for lines younger than 8s on the latest deal; history, reloads, past deals and reduced motion show everything at once. The pipeline/guard/result update in real time and can be ahead of the chat by a few seconds.
- `useRequestParse` now retries a failed preview itself (the composer used to stick after one failed call).
- README sections "Making requests" and "Going live" were lost in the last merge and are restored.

## Dashboard restructure (2026-10-09, samir/claude; uncommitted)
- Centre column is now tabbed: **Chat** (narrow 580px column, bubbles, round dividers), **Delivery** (sortable/filterable listings table, CSV export), **Timeline**, **Deals** (history; click a deal to inspect it, "Back to latest" returns). Audio controls are icon buttons in the tab bar.
- Left rail: Request (one-line "understood" preview), Mode (segmented control), Usage, run options. Right rail: wallet guard, escrow/verification.
- State: `deriveDealState(events, dealId)` + `dealsOf(events)` in `lib/eventReducer.js`; `lib/csv.js` (formula-injection-safe export). Tests: `npm test` (38).

## Current verification
- I01–I14 are complete. [Plan](../plan.md) has 19 open tasks; [archive](archive/COMPLETED.md) retains 31 completed IDs and acceptance notes. I13/I14 were delivered by parallel terminal sessions; other-owner changes were preserved.
- Latest combined backend suite and exact counts are recorded in [SYSTEM_CHECK.md](SYSTEM_CHECK.md). Frontend: 41 tests and production build pass. Synthetic Edge at 1920x1080 verifies keyboard Play/replay/speed/Stop/Mute, delayed ordered audio, stale labels and safe deal changes; zero page errors/overflow. Evidence: backend/data/i11-voice-ui/.
- Latest live HTTP check: one run of each act with subscription Max, scripted Viktor, cached real Apify, ElevenLabs and SIMULATED payments. Nine Codex turns, 27 speech clips, no fallback; actual buyer crash resumes with exactly one lock/payment, seller stays alive. Final balances 86/14/0. Evidence: backend/data/r-rehearsal-72848658/report.json. All owned services stopped.
- Earlier live attempts exposed ReadError between model turns. Buyer-owned HTTP clients now use fresh seller connections, avoiding idle keep-alive reuse without blindly retrying stateful offers. A real HTTP regression and the subsequent four-act run pass.
- The earlier three-runs-per-act R02/R05 acceptance remains historical evidence. The new run covers each act once, not a new full three-repeat acceptance or a timed two-minute recording.
- Optional subscription Viktor remains available; prior live two-agent Act 1 passed in 42.2s with 20 cached flats and seven clips. A recording profile using both live agents still needs O01.

## Data, agents and voice
- Permanent subscription-only model access: local ChatGPT-authenticated Codex CLI, labelled scripted fallback, no OpenAI API token/SDK. Both STAGED Act 2 agents remain scripted; code owns guard/floor/agreement decisions.
- I13: per-service Codex concurrency 2, queue wait 5s within the 30s turn deadline, failure threshold 3 and cooldown 15s; one recovery probe, bounded cancellation cleanup. [Runtime evidence](status/i13-runtime.md).
- I14: `uv run python scripts/readiness.py` from backend/ reports local profile/cache/sign-in/voice/storage prerequisites. Default starts no Actor runs, synthesis or payments; `--live-probe` explicitly checks enabled providers. [Readiness evidence](status/readiness.md).
- Data: validated Sreality rentals, exact-job atomic caches under `<APIFY_CACHE_PATH>.entries/`, legacy cache read compatibility. Default age limit 86400s; explicit stale offline override preserves timestamp and displays STALE CACHED DATA. Invalid/future/corrupt data fails closed.
- GET-only recovery `scripts/scrape_flats.py --run-id ZNboU2b0EHUJgFaEQ --report` inspected 22 valid records and selected 20; no new paid Actor run. Original completion time is retained. Validation reports count all rows and first rejection reason without printing raw records.
- Voice: exact text/voice/model cache with checksum and cancellation checks. Limits 512 files/128MiB count legacy clips; all published clips remain for replay, new unique speech uses text fallback when full. One buyer process per audio directory. Explicit voice readiness synthesis bypasses cached success.
- Transcript publishes before speech. Background speech is bounded (64 pending, two active); late audio binds to exact message/deal identity. Intentional-crash interruptions are labelled separately from provider failures and never regenerate paid audio on restart.
- Dashboard uses one player, ordered speech, saved-line replay and 0.75–2x speed. Stop/Mute and deal changes suppress late autoplay; readable text remains available. UI and event contracts: [INTERFACES.md](INTERFACES.md).

## Runtime and money boundaries
- The Haggle: buyer Max :8000, seller Viktor :8001, React/Vite dashboard :5173. Root `npm start` installs missing dependencies and starts all three; `npm run api/web` selects a side. Fresh-checkout local acceptance passed; every-laptop D01 remains open.
- Wallet guard cap 10, budget 20, approval above 8; con at 25 is blocked. Lost-payment replies retain recoverable intent, and restart does not pay an already-funded deal twice. Ledger binds real/simulated mode before recovery.
- `scripts/up.py --reset` archives only completed simulated ledgers; it refuses unfinished/real/mixed history and SQLite sidecars. Runner refuses occupied ports and stops only its own children. Existing .env, application ledgers and unrelated services were preserved.
- Masumi adapter/fake-node checks pass; hosted Railway node health/authentication/Preprod source were verified. Latest reported live blocker: funded transaction confirmed but node balance/registration pending; seller identifiers and actual live escrow remain unverified. Treat M02–M05/D05 as separate conditional gates.
- Act 4 refund is always SIMULATED. Real release is scheduled, not settled. Keep real/simulated ledger files separate. Seller jobs remain in memory: do not restart seller mid-funded-deal.
- Prior audits and merged team fixes remain in [SYSTEM_CHECK.md](SYSTEM_CHECK.md), [DECISIONS.md](DECISIONS.md) and [TRAPS.md](TRAPS.md); old test counts there describe their recorded snapshots.

## Release state
- [Video package](../video/README.md): four-act 1:55 script, storyboard, draft captions and capture/export handoff. Screenshots are not recorded footage. Final timed rehearsal, capture/edit/export and submission remain open.
- Recorded profile is SIMULATED unless live escrow is proven; do not infer Preprod readiness from adapter tests or the local checker. Feature freeze 04:00, video/repo 06:30, target submission 07:00, hard deadline 07:14 Prague time.
- Repository/history/public-access audit passed an earlier snapshot; F01–F03 require final revision/media evidence. No final video export or submission is claimed.
