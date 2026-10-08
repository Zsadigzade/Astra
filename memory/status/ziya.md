# ziya — status
updated: 2026-10-08 22:32
doing: I-path code integrated and offline checks green; live provider verification pending
touching: seller/apify.py + job.py, voice/, buyer/negotiator.py + orchestrator.py, dashboard audio, shared/, scripts/, tests/, docs/memory
blocked on: APIFY_TOKEN, ElevenLabs key + voice IDs; user confirms no OpenAI API key was supplied
next: scrape_flats.py -> genuine cache -> live/cached demo; voice_check.py -> select voices -> --synthesize/listen
done today:
- skeleton on main (ddfe809); Masumi client + masumi mode (fake-tested); OpenAI Max (untested live)
- 7 review fixes: crash resume, stored start, approval resume and simulated wallet top-up
- scripts/up.py + scripts/act.py; all 4 acts verified live in SIMULATED mode
- 22:07 masumi mode Act 1+3 rehearsed over real HTTP vs fake node: 1 payment, 1 purchase, already_paid after crash
- 22:14 readiness check fails on missing setup; node-only bootstrap + README runbook; 58 tests pass, no live payment attempted
- 22:17 plan has unassigned tasks/deadlines; stale navigation removed; generated folders hidden (cache deletion blocked by policy)
- 22:19 memory refreshed with main commits 036105e/1244aa6, task IDs, validation limits and reset caveat; other owners' status files preserved
- 22:32 I01/I02 adapters ready, I03 honest readiness check, I05 TTS hardened, I06 ordered queue integrated; 129 Python + 7 JS tests and build pass; no live provider result claimed
