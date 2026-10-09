# Judge deployment and presentation handoff

Updated 2026-10-09 05:56 Europe/Budapest.

The user authorized live agents/data/voices with strict limits and asked to check
Railway. The existing Railway Masumi node passes health/auth/source checks; there
is no Railway CLI login/token on this laptop. Real escrow remains unverified.

Gateway source: `0eb7881`, isolated checkout `backend/data/judge-source`; live gateway
9200 and private seller 9201, owned PIDs in `backend/data/judge-live/runtime.json`.
Limits: 12 total admissions, 3 per browser, 1 active run; persistent quota and isolated
ledgers/audio. SIMULATED money; paid provider usage may occur. Laptop must stay online.

The Cloudflare tunnel/DNS route for `astra.trainbud.site` is created, but automatic
approval review rejected starting it with only "blocked by policy" as the reason.
Explicit domain approval was requested and has not yet arrived. Do not claim a live
URL or put it in HQ. Do not bypass the rejection using a different process launcher.
After approval, start the prepared named tunnel and run
`backend/data/check_public_judge.py` once; this spends one of the 12 live runs.

Main advanced independently to `cb7a3be`. Preserve those changes. The merged UI at
`cc10f94` passed 679 backend tests, 63 frontend tests/build and three sample browser
cases with quota/isolation checks. The next recovery change passed 66 affected tests.
All 223 tracked files at `cb7a3be` passed the configured-secret check (7 values); the
three-commit delta since `d6b19a3` passed Gitleaks. New general-answer functionality
has no live acceptance in this deployment task. Do not switch the pinned judge source
without checking its added provider and network behavior.

HQ draft checked 05:55: project name is now **The Haggle** (preserved), both prize
checkboxes are selected, other prepared fields match, YouTube empty, Submit disabled.
The user will upload the accepted MP4 and provide its unlisted YouTube link.
Human listening review and a selected/timed stage speaker remain outstanding.

The portable kit remains `backend/data/presentation/Astra-presentation-kit.zip`;
the accepted 89.021333-second MP4 remains `backend/data/video/the-haggle-final.mp4`.
Latest testing is recorded in `backend/data/final-review-check/`. Temporary sample
and failed ngrok processes owned by this task were stopped. The live judge processes
and all other development/recording services were preserved.
