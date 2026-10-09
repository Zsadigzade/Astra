# I13 subscription runtime — complete

updated: 2026-10-09 01:45 +02:00 — I13 complete; shared memory reconciled
doing: complete — bounded concurrent subscription turns, queue waits and recovery cooldown
touching: backend/app/buyer/codex_runtime.py, backend/tests/test_codex_capacity.py, scoped Settings fields/.env.example/docs, this status file
coordination: I13 completed here; I14 completed by readiness session; I07–I12 remain with the parallel data/voice owner. Preserve their active edits.
scope: simulated tests only; no Actor runs, synthesis, money movement, service restart or ledger reset
next: parallel owners continue I07–I12; selected-profile rehearsal remains separate

Implementation:
- Shared per-service event-loop capacity (default 2), bounded queue wait (5s), consecutive-failure threshold (3), cooldown (15s), and one recovery probe after cooldown.
- Queue time consumes the existing total turn deadline. No seller transport deadline change or new SSE payload is required. Existing fallback_reason identifies CodexQueueTimeout/CodexCooldownError safely.
- Queued cancellation creates no process; running cancellation retains its slot until owned child-tree cleanup completes. Caller cancellations and rejected queue waits do not count as provider failures.
- Late completions from turns begun before cooldown cannot close/extend it. Successful probe restores normal turns; failed probe restarts only the local cooldown, without claiming provider reset timing.
- Scoped README, .env.example and INTERFACES entries document settings. Other sessions' shared-file edits preserved.

Acceptance: 145 focused runtime/capacity, Max/Viktor, guard and I14 readiness tests pass (3.67s), including six real local Python child processes capped at two and repeated-cancellation cleanup. No live inference, speech, scraping or payments were invoked. CLI login status separately confirmed ChatGPT sign-in; no subscription availability claim from that check.

Full shared working-tree regression: **523 backend tests passed in 51.99s**. Reproduce from `backend/` with `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=data/i13-full-tests-next`. Focused check selects `tests/test_codex_capacity.py tests/test_codex_runtime.py tests/test_llm_check.py tests/test_seller_persona.py tests/test_negotiator.py tests/test_guard.py tests/test_readiness.py`.

`git diff --check` passed. I13 marked complete in plan.md. Results cover the tested shared snapshot, including concurrent changes present during collection, not a final-release audit. No commit/push, runtime service changes, .env edits or ledger resets performed.

Memory update at 01:45: reconciled plan overview/ownership, HANDOFF, MAP and SYSTEM_CHECK; appended runtime policy and cancellation lessons to DECISIONS/TRAPS. Historical acceptance records and other owners' status files preserved. This follow-up changed documentation only; the test results above are from the completed implementation run.
