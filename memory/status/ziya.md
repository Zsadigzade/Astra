# ziya — status
updated: 2026-10-09 05:42 +02:00
doing: double-payment audit done; recovery gap fixed (uncommitted)
touching: backend/app/buyer/{guard,orchestrator,payments}.py, their tests, scoped memory
blocked on: nothing for this fix; commit is the user's call
next: review diff and commit; earlier launcher next-step below still stands
done today:
- 05:42 audit: no double-pay path; funded `paying` deal no longer blocked by limits lowered before restart (adapter `find` + `WalletGuard.recover`); 6 new regression tests, 593 backend pass.
- Built unsigned Windows x64 dist/AstraLauncher.exe (~11.4 MiB); repository/dependencies remain external as requested.
- Demo/recovery, readiness/live probes, full development tests/build and live four-act rehearsal controls.
- Sample checks need no keys; configured provider usage is explicit; all launcher payments are SIMULATED.
- Fresh ledger/audio/log/report directories; private smoke ports; busy interactive ports are preserved.
- Suspended child + Windows Job ownership prevents orphaned descendants; unrelated processes survive.
- EXE acceptance: readiness, 540 backend tests (13 launcher regressions), 50 frontend tests/build, real HTTP release/block/refund and balances pass.
- Final EXE GUI opens/closes cleanly; screenshot reviewed. Occupied-port/provider-usage failure reporting verified.
- Evidence: backend/data/launcher-bbb78291a3/report.json, data/launcher-exe-*.json, data/launcher-window.png.
- No new provider calls or real payments; existing .env/ledgers/other terminal services preserved.
- Earlier I07–I14 integrated: exact-job cache/freshness, subscription runtime, async voice/cache/replay and readiness.
- Earlier live four acts: 9 Codex turns, 27 clips, no provider fallback, actual buyer recovery and one payment.
