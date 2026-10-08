# Integrated system check — 2026-10-08/09

## I13 concurrency and recovery — recorded 2026-10-09 01:45 +02:00

- **145 focused tests passed in 3.67s** across subscription runtime/capacity, Max/Viktor, guard and I14 readiness. **523 full backend tests passed in 51.99s** on the shared working-tree snapshot; `git diff --check` passed.
- Concurrent deals share the configured service limit. Six actual local Python child processes never exceeded two simultaneous children. Queue expiry/cancellation starts no child; repeated cancellation retains capacity until owned child cleanup completes.
- Repeated CLI failures produce prompt labelled scripted fallback. Cooldown permits one later recovery probe; success restores turns, failure restarts the local cooldown. Late pre-cooldown completions cannot clear it. Caller cancellation and queue rejection do not count as provider failure.
- Queue waiting consumes the existing total turn deadline. Defaults: `CODEX_MAX_CONCURRENT=2`, `CODEX_QUEUE_TIMEOUT_SECONDS=5`, `CODEX_FAILURE_THRESHOLD=3`, `CODEX_COOLDOWN_SECONDS=15`. No API-token access or provider quota-reset prediction; guard/floor enforcement is unchanged.
- Reproduce from `backend/`: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=data/i13-full-tests-next`. Focused file list and implementation details: [runtime status](status/i13-runtime.md).
- I13 validation used local/fake providers, with no live inference, synthesis, Actor runs, payments, service restarts or ledger resets. The full-suite result includes concurrent changes present at collection; it does not sign off later edits, I07–I12's full acceptance, a final revision or a live-profile rehearsal. This memory update ran no new application tests.

## I14 local profile readiness — 2026-10-09 01:41 +02:00

- Added `backend/scripts/readiness.py`; run from `backend/` with `uv run python scripts/readiness.py`. Defaults inspect local configuration, Codex login status, cache contents and audio storage. They start no Actor runs, synthesize no speech and move no money.
- Completion check: `.\.venv\Scripts\python.exe -m pytest tests/test_readiness.py tests/test_llm_check.py tests/test_codex_runtime.py -q` — **62 passed** (30 readiness tests). Covers default-path provider isolation, actionable failures, output redaction, exact cache match/provenance, freshness/override, voice/storage settings, opt-in probe routing, bounded login output, timeout and cancellation cleanup.
- Actual local command: **exit 0** with subscription Max / scripted Viktor / CACHED APIFY / configured ElevenLabs. Twenty rentals matched; original cache timestamp `2026-10-08T21:05:09.035000+00:00`, run `ZNboU2b0EHUJgFaEQ`, dataset `mQFAkf7uENEXNnjN6`. Audio temporary write/read/remove succeeded.
- Sandbox could not confirm the existing Codex sign-in; approved execution outside the sandbox confirmed ChatGPT login. The checker never reads authentication files directly or prints credentials/child output.
- `--live-probe` opts into enabled subscription-agent and voice checks (voice credits). Probe routing was tested with fakes; no live probes, paid scrapes, speech synthesis, payment calls, service restarts or ledger resets were performed by this session.
- This is focused working-tree evidence, not full-suite/final-revision acceptance. Later I07–I13 changes need their owners' checks and any affected-profile rehearsal. Quota/model availability, voice access/synthesis, live escrow and full E2E remain unverified by the default command. Details: [readiness status](status/readiness.md).

## R02/R05 completion — 2026-10-09 00:51 +02:00

Final profile: `LLM_MODE=codex`, `SELLER_LLM_MODE=mock`, `APIFY_MODE=cached`,
`TTS_MODE=elevenlabs`, `PAYMENTS_MODE=simulated`; guard cap 10, approval above 8,
task budget 20, six negotiation rounds. Seller floor 7 for the four acts and 9
for the additional approval/decline checks. No new Apify scrape or real payment.

| Acceptance | Result |
|---|---|
| Act 1, three consecutive dashboard runs | Three releases at 7; 20 genuine cached listings verified each time |
| Act 2, three consecutive dashboard runs | Three agreements at 25 blocked before payment; intentionally scripted Max, STAGED labels |
| Act 3, three consecutive real crashes | Buyer exited after funding; restarted buyer alone; each deal had one escrow row, one lock, one already_paid and one release; seller PID survived |
| Act 4, three consecutive dashboard runs | Three junk deliveries rejected and refunded; STAGED / SAMPLE DATA labels |
| Approval and decline at 9 | Both dashboard buttons work; no payment before approval, no payment on decline |
| Provider evidence | 35 subscription Max turns, 100 newly generated and HTTP-served ElevenLabs clips; zero model or voice fallbacks |
| Accounting | Seven releases, four blocks, three refunds; final balances 49 buyer / 51 seller / 0 escrow, conserving 100 |
| 1920×1080 recording frame | 16 exact-size Edge screenshots; negotiation, guard, outcomes and approval controls fit; no horizontal overflow or page errors |
| Automated checks | 392 full backend tests pass on Python 3.13 (43.32s), including 25 focused act/recovery tests; 33 frontend tests and production build pass |

Representative screenshots were visually inspected for the successful deal, red guard
block, recovery's “Not paid twice” badge, refund checks and pending approval. The browser
kept voices stopped during screenshots; this run verifies synthesis/HTTP delivery, while
actual sequential playback remains covered by the earlier recorded browser acceptance.
The 285.3 seconds summed over these 14 automated cases is not the two-minute video rehearsal.

Fixed deliberate Act 3 startup to persist `staged=true` on `task_created`; replay keeps
the dashboard's STAGED label after restarting with the crash flag cleared. Two regression
cases also ensure ordinary honest deals remain unstaged.

Reproduce from backend with `uv run python scripts/rehearse.py`, adding `--browser`
with Playwright/Edge installed for layout acceptance (see README). New ledgers, ports,
audio and logs are isolated per invocation. Successful evidence is in
`backend/data/r-rehearsal-29b87432/report.json` and its 16 PNGs; all owned services stopped.
Earlier attempts hit an in-progress I04 configuration edit, sandboxed Vite reads, and
an ambiguous STAGED badge selector; they are retained separately and not counted as the
complete acceptance run. Subscription Viktor and live Preprod need their own rehearsals.

## I01–I06 completion — 2026-10-09 00:42 +02:00

- Isolated I-only staged source export also passes all 390 backend tests on Python 3.13 (36.90s) and 3.11 (30.41s). This excludes the concurrent R/video edits; snapshot: backend/data/i-staged-501319f3/source/.

- I04 now supports subscription Viktor via optional SELLER_LLM_MODE=codex; defaults preserve the scripted-seller rehearsal profile. No API keys or new payment integration.
- Real Viktor checker produced opening 18 and accepted 7 without fallback. Full two-agent HTTP Act 1 used three Max and four Viktor Codex turns, 20 genuine cached Apify listings and seven new ElevenLabs clips; no model/voice fallback, SIMULATED release in 42.2s.
- Strict seller outputs, floor/agreement enforcement, same-round retry deduplication, stale-round conflicts, cancellation and staged-con isolation have regression coverage. Buyer forwards actual seller provenance; its HTTP deadline allows seller CLI cleanup/fallback.
- Shared-workspace validation: 392 backend tests on Python 3.13 (36.25s) and Python 3.11 (27.54s), including two concurrent R-path staging regressions. Frontend: 33 tests and build pass; rendered Edge checks cover live/fallback/legacy seller labels, both-agent usage and mixed-mode header, with zero page errors.
- Evidence under backend/data/: i-complete-97ac1034/ (fresh live deal, seven clips, events/report), hour-seller-ui-report.json (rendered labels). Existing .env, ledgers and parallel R/video work are preserved. I04 is opt-in; changing the final video profile requires its own R02 rehearsal.

## Video and release preparation — 2026-10-09 00:39 +02:00

- V01: [four-act script and evidence storyboard](../video/script.md) targets 1:55 with five seconds spare; guard, buyer crash recovery and honest limitations included. Narration/caption timing is a plan, not a measured rehearsal.
- Document checks: 192 spoken words; 25 ordered, nonoverlapping SRT cues match the narration exactly, end at 113 seconds and use at most two lines/44 characters per line. All 47 local links in reviewed docs resolve; checklist count is 20/35 and whitespace checks pass.
- V02–V04: [capture/export handoff](../video/production.md) and [draft SRT](../video/narration-draft.srt) prepared. No footage, final voiceover or exported video produced; final layout, R02/R05 and recording remain separate acceptance gates.
- V05: reviewed baseline run instructions, environment template, architecture and limitations; linked the video package from README/MAP/HANDOFF. Active I04 changes still require their own final-profile documentation reconciliation.
- V06: Gitleaks 8.30.1 with release checksum verified; full Git diff scan plus complete contents of 476 blobs and all 48 reachable commit objects, including both remote branches and local auxiliary refs. Five configured local secret values also checked: no matches. All scanner findings are exact occurrences of the documented non-credential Apify run ID, reviewed without suppressions. Remote tips match local coverage; repository is not shallow. GitHub reports public and an unauthenticated API request returns HTTP 200 with `private: false`. [Audit scope and rerun instructions](../video/release-audit.md); repeat after final code/media changes.

## Scoped audit — 2026-10-09, closed when the user returned

Scope: existing Ziya data, subscription-agent, voice and integration paths. Murad's
launcher and follow-up audit commits through 3b10519 are integrated and revalidated;
Mais's active funding branch is retained. The planned 50-minute endurance run stopped
after 20m55s when the user returned. Only completed checks are counted below.

| Check | Result |
|---|---|
| Backend | 364 passed on Python 3.13 (28.84s) and fresh Python 3.11 (33.05s), including Murad's latest bounds/CORS changes |
| Frontend / browser | 32 tests; production build; 11 fresh Edge dashboard scenarios pass with zero page errors |
| Live providers | Three real subscription Codex turns, 20 genuine cached Apify flats, seven new ElevenLabs MP3s; SIMULATED release in 21.8s, no text fallbacks |
| Voice playback | Real Edge MP3 playback: order, replay dedupe, reset identities, missing clip skip, Stop/Mute, destroy and watchdog pass; maximum one clip playing |
| Clean checkout | No .env/cache/dependencies initially; npm start installs dependencies, starts all three services and completes a sample-data SIMULATED deal |
| Terminal | Ten real-HTTP scenarios pass: honest, con, junk, latest-deal replay, approve, replay approved, decline, replay declined, paused and offline |
| Endurance | 21 cycles in 1255.2s; 63 refunds, 44 blocked, 21 walkaways, seven releases; five concurrent batches and one corrupted-cache refund; zero failures |
| Recovery during endurance | One actual crash after funding recovered with exactly one lock; two pending-approval restarts preserved consent; seller remained running |
| Endurance cleanup | Zero pending tasks/approvals/SSE subscribers; balances 51 buyer / 49 seller / 0 escrow, conserving 100; only the audit's owned processes were stopped |

Fixes: repeated Codex cancellation and process cleanup; bounded model/MP3 output;
strict cached records and run identity; seller response/deal/round/job/price binding;
failed jobs cannot release with stale results; invalid legacy tasks preserve their
rows and cannot stop valid recovery; terminal replay ignores old deals and stale
approvals. Strict integer rents prevent seller-response coercion; malformed URL ports
and control characters fail verification. Tests now default to LEDGER_PATH=:memory:
even without a shell override.

Local evidence under backend/data/: hour-clean-start-2929d7ee/,
hour-cli-125ea4c3/, hour-voice-browser-report.json, system-live-91702a89/,
system-dashboard-0bb1bbaa/ (latest team-commit browser check), system-dashboard-41ade425/
(earlier check), and hour-endurance-97549284/ (stopped on return, not a 50-minute pass).
All payment tests are SIMULATED or use the fake Masumi node. No new paid Apify run.
Endurance deliberately exercised unavailable-Codex/text fallbacks; it does not complete
three consecutive full-profile live-provider rehearsals. That remains R02 in plan.md.

## Earlier integrated audit

Audited main at 8a24b38, including Murad's dashboard/operator controls, Mais's Masumi schema fix,
and Ziya's subscription, data, voice, ledger and runner changes. Murad's UI update 2d0d987 arrived
before push; it was merged with the audit fixes and passed fresh frontend/browser revalidation.
Fixes and this report are committed together.

## Final verification

| Check | Result |
|---|---|
| Complete backend suite | 255 passed (16.74s), isolated LEDGER_PATH=:memory: |
| Frontend suite / production build | 32 passed / build passed |
| Fresh browser scenarios | Honest release; staged con blocked; junk refunded; approval accepted and declined |
| Dashboard controls | Pause/resume, paused task rejection, runtime rounds, visible request failures |
| Browser resilience | Actual buyer stop/restart, SSE replay without duplicate transcript, theme persistence, no horizontal overflow at 390/1000/1100/1440px; zero page errors |
| Actual runner crash recovery | One lock, one staged buyer restart, seller survives, one already_paid event, one release; SIMULATED balances 93/7/0 |
| Actual reset | Configured completed ledger archived byte-for-byte; new ledger empty; only owned processes stopped |
| Subscription access | Live Codex checker passes; fresh Act 1 uses three Codex turns, settles at 7 |
| Apify | GET-only recovery returns 20 valid listings from ZNboU2b0EHUJgFaEQ; no new paid scrape |
| ElevenLabs | Voice discovery and two new samples pass; fresh Act 1 generates and serves seven MP3s with no text fallbacks |
| Integrated live-provider Act 1 | 20 cached genuine listings verified, SIMULATED escrow released in 22.8s |
| Latest UI subscription/audio replay | Codex, cached-data and SIMULATED labels visible; five saved MP3s play once in order without overlap/media/page errors; controls pass |
| Hosted Masumi | Final node-only check passes health, authentication and one Preprod Cardano payment source |
| Local seller readiness | Fails: MASUMI_AGENT_ID missing; SELLER_VKEY missing/invalid; registration and wallet setup still needed |

## Defects fixed

- Preserve payment intent after a lost lock response so restart resolves the same payment instead of abandoning potentially funded work.
- Reject nonfinite money/guard values and nonpositive/nonfinite task budgets.
- Reject misleading district matches (Praha 70), nonpositive rent and malformed URLs; accept sample and genuine Apify locality suffixes.
- Require confirmed Masumi result submission/release state before reporting scheduled release; otherwise keep escrow recoverable.
- Cancel buyer-owned tasks before closing HTTP resources on shutdown; preserve pending approval for restart.
- Keep provider response bodies out of Masumi errors surfaced through logs/dashboard events.
- Use declared runner service ports consistently for startup and restart checks.
- Handle pause failures visibly, disable offline pause controls, and preserve simulation labels during disconnects.
- Keep funded errors and scheduled releases in escrow totals; distinguish scheduled from completed release and current-task budget from lifetime usage.
- Preserve the latest UI layout while correcting its API-era mode check so subscription Codex is not labelled SCRIPTED AGENTS; scripted seller identity remains explicit.

## Limits and evidence

All payment rehearsals above used SIMULATED money or the test Masumi service. Live Preprod
escrow, wallet funding, Viktor registration and every-laptop acceptance are not verified.
Initial hosted access returned 401; the final recheck passes with the current local configuration.
No secrets were logged. The remaining configuration blockers are MASUMI_AGENT_ID and SELLER_VKEY.
Existing application ledgers, .env and unrelated running services were preserved.

Ignored local artifacts: system-dashboard-4bd095d7/ (final merged UI browser checks/screenshots),
system-runner-audit-6872233b/ (crash/reset report), system-live-ca49c10c/ (fresh live-provider deal),
system-check-20261008/ (recovered data and voice samples), and i-path-smoke-d2448b5d/ (latest UI subscription/audio replay). These paths are relative to backend/data/.
Earlier isolated attempts retained their own ledgers: an intermediate verifier rejected valid suffixes;
the final corrected code passes both sample and genuine cached data. Only final runs are counted above.
