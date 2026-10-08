# R integration acceptance

updated: 2026-10-09 00:53 (Europe/Budapest)
doing: complete — R02 and R05 accepted; all R checklist items now checked
touching: backend/scripts/rehearse.py, crash-label line in orchestrator.py, test_acts.py, README and R evidence/checklist/handoff
profile: subscription Codex Max, scripted Viktor, cached real Apify, ElevenLabs, SIMULATED payments
isolation: new ledger/audio directory and unused ports; preserve existing services, ledgers, .env and other owner status files
next: video owners can use the accepted profile/layout for V02–V04; repeat R02 if changing seller or payment profile

coordination: I04 completed during this session; R explicitly pins SELLER_LLM_MODE=mock for the plan's final baseline. Only R edit in orchestrator.py is the task_created staged flag for deliberate crash; concurrent I04 changes preserved. Video/status/ziya changes belong to their owners.
verified: 392 backend tests (43.32s), 33 frontend tests and production build pass. The two new regressions prove deliberate crash labels survive event replay while ordinary honest deals stay unstaged.
R02: three consecutive runs per act plus approve/decline; 14 outcomes, 35 Codex turns, 100 real MP3s, zero fallbacks. Three actual buyer crashes each recover with one lock, one already_paid and one release while seller stays alive. Final balances 49/51/0; no reset/top-up.
R05: 16 exact 1920x1080 Edge screenshots, no page errors/overflow; frame checks plus representative visual inspection cover negotiation, red blocked guard, release/refund, recovery, approvals and honesty labels. All owned services stopped.
evidence: backend/data/r-rehearsal-29b87432/report.json, screenshots, retained isolated ledger/audio/logs. Earlier incomplete attempts retained separately; no existing runtime data or .env changed.
limits: browser voices stayed stopped during screenshots; new clips were synthesized and served successfully, with actual playback covered by prior acceptance. Screenshots are not video footage or a timed two-minute rehearsal. No live Preprod gate claimed.
