# Current submission handoff - 9 October 2026

- **05:42:** double-payment audit: no double-pay path found. Fixed one recovery gap (funded
  `paying` deal blocked and its escrow stranded when limits were lowered before restart); see
  TRAPS 05:42. Uncommitted: `backend/app/buyer/{guard,orchestrator,payments}.py` + tests
  (test_guard, test_resume, test_masumi, test_llm_check). After merging origin/main (`cc10f94`)
  685 backend and 63 frontend tests plus build pass. Recording code `1d9173c` unaffected.
- **05:28:** friend owns UI/UX, expected around 05:50; preserve the accepted MP4 while
  checking that handoff. No UI edits in this presentation pass. Remaining operator
  controls passed in isolated services without provider calls; copied ledger reset
  preserved bytes. Presenter HTML/timer and offline PDF/PNG/ZIP are ready; see [production](../video/production.md).
- User explicitly opted into **Best ElevenLabs Use**; saved HQ checkbox reload verified.
  All prepared fields persist. Submit remains disabled without the YouTube URL.
  Speaker choice, human listening/timed pitch, final UI acceptance and submission remain open.

- Recording code `1d9173c`; full live-provider capture passes all four acts plus approve/decline with SIMULATED escrow. 579 backend / 63 frontend tests and build pass. Nonsecret results: [video/evidence.json](../video/evidence.json).
- HQ now requires **90 seconds**, not two minutes; **Unlisted YouTube** is mandatory. The approximately 89-second export is `backend/data/video/the-haggle-final.mp4`. User will upload and send the link; HQ project draft is saved, not submitted.
- **60-second stage pitch**, presentations **09:30**, target submit **07:00**, close **07:14**, Prague/Budapest. [Pitch and jury answers](../video/script.md), [operator runbook and take index](../video/production.md).
- Apify reports real paid provider usage (Act 1 USD 0.110573). Keep this distinct from SIMULATED agent escrow; no actual Masumi transfer, settlement or provider refund is claimed.
- Current local services are healthy with live providers and authenticated buyer access. No public hosting is required for the HQ form or prepared here. Do not expose the dev dashboard/token.
- Earlier handoffs below are historical, including references to cached data, scripted con, in-memory seller jobs, old test counts and a two-minute edit.

# Handoff — integrated main

## Merge integration (2026-10-09 04:27 +02:00)

- Merged remote dashboard/conversation changes with local authentication, durable seller state
  and live-con changes. Preserved the new ghost stage and API token on voice playback; frontend
  test command includes both eye-tracking and authentication suites (63 tests and build pass).
- Max's fixed opening question remains labelled scripted. Rehearsal excludes only that
  non-fallback greeting from live-decision counts; strict-live failures still cannot produce
  scripted offers. Browser rehearsal opens the Wallet tab before checking policy framing.
- Final merged validation: 579 backend tests, 63 frontend tests and production build passed.
  No new live-provider or browser rehearsal was run for this merge.
- Older entries below describe their historical snapshots, including their then-uncommitted state.

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

## Page fill, flat chat, new logo (2026-10-09, samir/claude; uncommitted)
- Layout is full-bleed (no 1600px cap, rails 260/320, 290/370 on very wide screens). Nothing floats in the middle: the stage is a full-width tinted band with Max at the left edge, Viktor at the right and the price coin + offer ladder between them. The left rail spreads its cards through the height (Request, Recent, Mode, Usage, options); on short screens the examples/recent rows compact so no rail needs a scrollbar at 1366x768.
- Before a request the page shows the same band plus "How a deal works" and "Try one"; the right rail shows Wallet policy, Setup (what powers Max/Viktor/voice/money) and Balances.
- Chat rows are flat (avatar, name, round, time, text, price line, no boxes) with a typing row for the agent about to speak. New "Recent" card lists the last five requests and reopens them.
- Ghost size/position: 140px (164px on very large screens, 124/108px on shorter ones), up from 96px, and moved in toward the price coin and offer ladder instead of the band edges. Drawing unchanged.
- Logo: two interlocking speech bubbles (buyer blue, seller violet) sharing one white agreed spot; same mark as the favicon. The ghost drawings are untouched.

## Conversation order, board and right-rail chat (2026-10-09, samir/claude; uncommitted)
- Max opens every deal with a question ("Hi Viktor. Can you get me ...? What is your price?"), then Viktor answers with his ask (`orchestrator.haggle`, template line, backend `mock`, voiced like any other line).
- Layout: the transcript is now the right rail's top card (`ChatFeed`), replacing Wallet policy there; Balances and Delivery and verification stay under it. Wallet policy moved to a centre **Wallet** tab. Centre tabs: Results, Wallet, Timeline, Deals; the ghosts sit above the tabs.
- Results board (`ResultsBoard`): an offer ladder whose chips appear as offers are made, then the listings, which wait until the conversation has finished, fade in row by row and are marked Accepted (or Rejected) by Max from the verification result.
- Pacing: speech bubbles stay `1.2s + 40ms/char` (1.6s to 5.5s), the next line waits for the bubble to end. Only lines created AFTER the page loaded are paced; a reload or an older deal shows everything at once. Purely cosmetic, the guard/pipeline/result still update in real time.

## Cursor-following eyes (2026-10-09, samir/claude; uncommitted)
- Before a request is given the empty state shows the two ghosts (the existing drawing, unchanged) and their eyes follow the cursor (`hooks/useCursorEyes.js`, maths in `lib/eyes.js`, 5 tests). Typing keeps them following; pressing Run stops it for the rest of the page session (a reload re-arms it). It also works in the deal view when the ledger has history (the page then opens there, not in the empty state). Off under `prefers-reduced-motion`.
- Appearance was deliberately NOT changed (owner request): same ghost drawing, size, colours, logo. A first attempt at new character art was backed out. Viktor's drawing is mirrored, so his horizontal eye/tilt direction is flipped in CSS.

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
