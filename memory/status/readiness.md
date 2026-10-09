# Readiness session — I14

updated: 2026-10-09 01:41 +02:00
doing: I14 complete — unified data/agent/voice readiness command
touching: backend/scripts/readiness.py, backend/tests/test_readiness.py, README.md (I14 usage paragraph), plan.md (I14 completion and checklist note), memory/status/readiness.md
coordination: ziya.md owns I07–I12; i13-runtime.md owns I13. This session owns only I14. Reuses load_cache and existing agent/voice checks; no runtime/UI/payment changes. Reads additive cache_stale when available.
next: parallel owners continue I07–I13; rerun readiness on each selected laptop/profile before rehearsal
blocked on: nothing

## Acceptance evidence

- From `backend/`: `.\.venv\Scripts\python.exe -m pytest tests/test_readiness.py tests/test_llm_check.py tests/test_codex_runtime.py -q` — **62 passed** (30 readiness tests).
- Covers sample/cached/live configuration, exact cache match and preserved provenance, expired cache and explicit stale override, missing credentials, invalid provider limits, unwritable audio storage, safe failure output, opt-in probe routing, login output bounds, timeout and cancellation cleanup.
- Default-path tests forbid HTTP/provider probes and Actor calls. Probe tests use fakes; no provider credits spent.
- Actual `.\.venv\Scripts\python.exe scripts/readiness.py` — **exit 0** on local profile: subscription Max, scripted Viktor, 20 CACHED APIFY rentals, configured ElevenLabs, writable audio storage. Cache fetched at `2026-10-08T21:05:09.035000+00:00`, run `ZNboU2b0EHUJgFaEQ`, dataset `mQFAkf7uENEXNnjN6`.
- Initial sandbox invocation could not confirm Codex sign-in; approved execution outside the sandbox confirmed ChatGPT login. No auth files are read directly, copied or printed.
- No live probes, Actor runs, speech synthesis, payments, service restarts or ledger resets. Quota/model access, voice access/synthesis, live escrow and full E2E remain outside this local check.
- README usage and I14 plan entry updated. Shared runtime/cache/UI implementation belongs to parallel sessions and was preserved.
- Shared memory reconciled: MAP links this status and the I13 owner; HANDOFF records I14 completion and ownership; SYSTEM_CHECK records scoped evidence; DECISIONS/TRAPS record the local-default policy and sandbox sign-in limitation. No new runtime checks were performed for this documentation-only update.
