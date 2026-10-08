# Runner reliability — parallel session

updated: 2026-10-08 23:26
doing: complete — runner fixes, shared mode-check integration and documentation verified
touching: backend/scripts/up.py, backend/tests/test_up.py, this status file; targeted reset wording in README/HANDOFF/INTERFACES
coordination: preserving existing dirty files; LLM/config/dependencies and dashboard belong to other active sessions
scope: R03/startup reliability; no live service restarts, provider calls, or runtime ledger resets
next: all-laptop/live rehearsal remains with demo owners; no R03 acceptance claim from unit tests

23:22 coordination: read reliability.md and adopted ledger.payment_mode(db) in reset preflight.
It now rejects even an empty Masumi-bound ledger and mixed stored job/payment evidence.
Initial runner tests: 25 passed. Full shared backend suite: 213 passed (26.22s).
Shared mode-check regressions complete: 48 runner + ledger-mode tests pass, including 27 runner tests.
Reset-related documentation now describes configured-path archival and refusal conditions.

Completed fixes:
- Occupied ports fail before reset/startup; readiness rejects exited child processes.
- Partial startup cleans up only processes launched by this runner; forced kills are waited on.
- Reset preserves a timestamped backup, respects custom LEDGER_PATH, and rejects unfinished,
  held-escrow, real/mixed-mode, corrupt or SQLite-sidecar ledgers.
- Only configured staged crash mode gets one buyer restart; restart sets CRASH_AFTER_LOCK=0
  even when the flag originated in .env. Failed recovery reports failure, not success.
- Tests use temporary ledgers and controlled processes; no live services were restarted or ledgers reset.
- Initial pytest invocation hit sandbox temp/cache permissions; approved reruns used distinct workspace
  basetemp directories with pytest's shared cache disabled to avoid parallel-session interference.

Final validation at 23:24: 215 backend tests passed in 15.07s, with LEDGER_PATH=:memory:
for module-level buyer creation. Runner --help works from the repository root; scoped diff check passes.
Changes remain uncommitted in the shared working tree to preserve the active sessions' work.

23:26 memory reconciliation: preserved concurrent MAP/DECISIONS/TRAPS and owner-status updates.
Final runner validation remains 215 full backend tests in 15.07s at 23:24, including 27 runner tests;
48 combined ledger/runner tests passed after mode-check integration. All-laptop and live Masumi gates
remain unclaimed. At 23:25, locally known origin/main was 3 commits ahead; no pull or branch operation
performed. Parallel Ziya status now reports the live subscription check and Act 1 passed at 23:25.
