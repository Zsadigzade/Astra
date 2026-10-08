# Reliability session — status

updated: 2026-10-08 23:25 (Europe/Budapest)
doing: ledger payment-mode isolation complete and verified
touching: backend/app/buyer/ledger.py, backend/app/buyer/payments.py, backend/tests/test_ledger_mode.py
coordination: parallel sessions already editing model configuration/dependencies/checker, verifier, frontend App and ziya status; leave those files to their owners
blocked on: nothing for local reliability work
next: mode-check integration is complete; demo owners continue all-laptop/repeated-act rehearsals and live Masumi setup using separate ledgers
scope: local reliability work supporting R01/R03; no live payment or all-laptop acceptance claim

23:18 coordination: runner-reliability session is actively changing scripts/up.py. Leaving all runner/reset edits and tests to that session. New ledger.py payment_mode(db) reads stored metadata plus legacy evidence; bind_payment_mode(mode) rejects mode mismatches/mixed ledgers before either adapter is constructed. Runner reset should consult payment_mode(db) to reject a Masumi-bound empty ledger as well. No changes to up.py made by this session.

done:
- Atomically persist payments_mode in ledger_metadata before constructing either payment adapter. Restarting with the opposite mode fails before wallets/client creation or deal recovery.
- Infer older ledgers from simulated tables, escrow references, stored start responses and SSE event flags; reject contradictory/corrupt history and payment activity with no mode evidence. Preserve existing history.
- Reject unknown PAYMENTS_MODE values instead of silently selecting simulated payments.
- Added backend/tests/test_ledger_mode.py. Focused ledger/guard/resume/acts/fake-Masumi suite: 45 passed. Full backend suite on the concurrent working tree at 23:22: 213 passed in 25.61s.
- Tests used LEDGER_PATH=:memory: for module-level app creation and temporary ledgers/fake services. No real payment, provider call, service restart or runtime reset performed.
- Pytest required sandbox escalation for Windows temporary-directory access; initial full collection raced ongoing negotiator changes, final full run passed.

Coordination resolved: runner owner adopted payment_mode(db) in reset preflight and added regressions for empty Masumi-bound ledgers and conflicting stored evidence. Combined ledger + updated runner suite: 48 passed in 3.72s. Runner remains responsible for up.py and its documentation; no overlapping edits made here.

23:25 memory refresh: updated HANDOFF/MAP/INTERFACES and appended decisions/traps for these material changes. Runner owner reports a final full suite of 215 passing tests at 23:24; this session directly verified 213 before the last two runner tests and then all 48 combined ledger/runner tests. Changes remain uncommitted alongside other sessions' work. No D01/R01/R03 or live-payment acceptance gate marked complete.
