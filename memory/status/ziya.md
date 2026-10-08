# ziya — status
updated: 2026-10-09 00:42
doing: I01–I06 complete and pushed to main; subscription Viktor live-verified
touching: seller persona/negotiation, provenance contracts/UI, LLM checker/tests, configuration and I-path docs/memory
blocked on: nothing for I path; live Masumi remains outside this task
next: preserve scripted-seller rehearsal baseline; enable SELLER_LLM_MODE=codex only when selecting the two-live-agent profile
done today:
- I completion: isolated commit passes 390 backend tests on Python 3.11/3.13 (392 with pending R tests); 33 frontend tests/build and Edge provenance checks pass.
- Live two-agent Act 1: 3 Max + 4 Viktor Codex turns, 20 genuine cached flats, 7 voice clips, no fallback; SIMULATED release in 42.2s.
- Clean-checkout npm start and 10 real-HTTP terminal scenarios pass; replay selects the latest deal and skips stale approvals.
- Endurance stopped on return at 20m55s: 21 cycles, 135 outcomes, five concurrent batches; no failures or pending work; SIMULATED balances 51/49/0.
- Fixed repeated Codex cancellation, strict move/cache/rent validation, bounded TTS, seller-response binding, legacy recovery and terminal replay.
- Audited merged work from Ziya, Murad and Mais, including late UI update 2d0d987; latest frontend tests/build/browser rerun pass.
- Fixed lost-payment-response recovery, invalid money inputs, delivery verification and unconfirmed Masumi release reporting.
- Fixed buyer shutdown cleanup, provider error-body exposure and runner port consistency.
- Fixed offline pause errors, escrow/scheduled-release totals, task budget display and control wording.
- All I01–I06 checklist items are verified; R/video sessions own their remaining acceptance work. Existing .env stays unchanged.
- Browser: all three UI acts, approve/decline, controls, offline/reconnect, theme and responsive widths pass; zero errors.
- Final hosted Masumi node-only check passes health/auth/Preprod source; initial 401 resolved.
- Details and local evidence paths: memory/SYSTEM_CHECK.md. Existing ledgers, .env and unrelated services preserved.
