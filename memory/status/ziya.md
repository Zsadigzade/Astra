# ziya — status
updated: 2026-10-08 23:53
doing: full audit and latest UI merge complete; all fixes verified
touching: backend guard/recovery/verifier, Masumi errors, runner, dashboard controls/accounting, tests, shared memory
blocked on: MASUMI_AGENT_ID missing and SELLER_VKEY missing/invalid; funding/registration/live escrow not verified
next: complete seller registration/configuration and funding, then validate live Preprod escrow
done today:
- Audited merged work from Ziya, Murad and Mais, including late UI update 2d0d987; latest frontend tests/build/browser rerun pass.
- Fixed lost-payment-response recovery, invalid money inputs, delivery verification and unconfirmed Masumi release reporting.
- Fixed buyer shutdown cleanup, provider error-body exposure and runner port consistency.
- Fixed offline pause errors, escrow/scheduled-release totals, task budget display and control wording.
- Final checks: 255 backend tests, 32 frontend tests and production build pass.
- Browser: all three UI acts, approve/decline, controls, offline/reconnect, theme and responsive widths pass; zero errors.
- Real runner: one staged crash/restart, one payment, successful recovery; safe reset preserves archive bytes.
- Fresh live-provider Act 1: three Codex turns, 20 cached genuine Apify listings, seven new voice clips, SIMULATED release at 7.
- Apify GET-only recovery and ElevenLabs discovery/two samples pass; no new paid scrape.
- Final hosted Masumi node-only check passes health/auth/Preprod source; initial 401 resolved.
- Details and local evidence paths: memory/SYSTEM_CHECK.md. Existing ledgers, .env and unrelated services preserved.
