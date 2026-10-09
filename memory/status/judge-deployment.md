# Judge deployment and presentation handoff

Updated 2026-10-09 06:05 Europe/Budapest.

Published and signed-out verified: **https://astra-haggle-judges.vercel.app**.
The user explicitly selected recording/presentation hosting while keeping the current
network. The page serves the unchanged MP4, existing seven-slide HTML deck, PDF and
repo link. It clearly states that live interactive access is unavailable. No provider
keys, runtime state, application backend or Codex sign-in were uploaded.

Evidence: `backend/data/judge-live/vercel-public-acceptance.json` (four public asset
hashes match, video playback/seek/ranges pass, seven slides navigate, mobile fits,
zero page errors). Deployment `dpl_7W8bKB9nV5WbBVhmrnDEJsk8kAdr`, status READY.
The page does not depend on the laptop staying online.

The user authorized live agents/data/voices with strict limits and asked to check
Railway. The existing Railway Masumi node passes health/auth/source checks; there
is no Railway CLI login/token on this laptop. Real escrow remains unverified.

Gateway source: `0eb7881`, isolated checkout `backend/data/judge-source`; live gateway
9200 and private seller 9201, owned PIDs in `backend/data/judge-live/runtime.json`.
Limits: 12 total admissions, 3 per browser, 1 active run; persistent quota and isolated
ledgers/audio. SIMULATED money; paid provider usage may occur. Laptop must stay online.

The Cloudflare tunnel/DNS route for `astra.trainbud.site` exists. After the user
authorized the Vercel/tunnel combination, startup executed but failed because this
network refused Cloudflare edge DNS. An additional DNS troubleshooting command was
blocked by automatic approval review ("blocked by policy"). The user then selected
the recorded-page fallback. No public live run occurred. No further tunnel work is
pending under the current instruction; keep the isolated gateway available locally.

Main advanced independently to `cb7a3be`. Preserve those changes. The merged UI at
`cc10f94` passed 679 backend tests, 63 frontend tests/build and three sample browser
cases with quota/isolation checks. The next recovery change passed 66 affected tests.
All 223 tracked files at `cb7a3be` passed the configured-secret check (7 values); the
three-commit delta since `d6b19a3` passed Gitleaks. New general-answer functionality
has no live acceptance in this deployment task. Do not switch the pinned judge source
without checking its added provider and network behavior.

HQ draft updated 06:05: the limitations field includes the verified Vercel URL as
recorded-only materials. Live Demo stays blank. Project name **The Haggle** and both
prize checkboxes are preserved. YouTube is still empty; no submission was made.
The user will upload the accepted MP4 and provide its unlisted YouTube link.
Human listening review and a selected/timed stage speaker remain outstanding.

The portable kit remains `backend/data/presentation/Astra-presentation-kit.zip`;
the accepted 89.021333-second MP4 remains `backend/data/video/the-haggle-final.mp4`.
Latest testing is recorded in `backend/data/final-review-check/`. Temporary sample
and failed ngrok processes owned by this task were stopped. The live judge processes
and all other development/recording services were preserved.
