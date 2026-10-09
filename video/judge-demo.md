# Judge demo deployment

The user selected live agents, data and voices with a strict usage limit. The public
gateway is separate from the recording/development services. Agent payments remain
SIMULATED; no Masumi funding or live escrow is claimed.

## Published Vercel page — 06:05

**https://astra-haggle-judges.vercel.app** is public and verified without sign-in.
It serves the accepted 89.021333-second video, the existing `the-haggle.html`
presentation, its PDF, and a source link. It clearly says **recorded demo** and
**interactive live access unavailable**. It works independently of this laptop.

The user chose to keep the current network and publish these recorded materials
after the tunnel's DNS lookup was refused. The later tunnel start was authorized and
executed, but Cloudflare could not resolve its edge service records. An additional
DNS troubleshooting command was blocked by automatic approval review. Do not continue
tunnel troubleshooting or substitute another public live path without new direction.

Production deployment: `dpl_7W8bKB9nV5WbBVhmrnDEJsk8kAdr`. The five-file package
passed configured-secret scanning. Public verification checked hashes for the page,
MP4, HTML deck and PDF; video byte ranges, playback and seeking; all seven slides;
phone layout; and zero browser page errors. Evidence:
`backend/data/judge-live/vercel-public-acceptance.json` and `vercel-manifest.json`.

HQ's limitations field includes this URL with the recorded-only qualification.
The optional Live Demo field remains blank. The required Unlisted YouTube link is
still pending; this Vercel page does not replace that requirement.

Build/publish instructions: [Vercel package](../deploy/vercel/README.md).

## Prepared runtime

- Inactive backend candidate: `https://astra.trainbud.site`. DNS route exists, but
  tunnel startup failed on network DNS. It is not a working demo URL and is not in HQ.
- Private gateway: `127.0.0.1:9200`; private seller: `127.0.0.1:9201`.
- Source: isolated checkout `backend/data/judge-source`, committed as `0eb7881`
  on `judge-demo-20261009`. Later main-branch changes are not deployed here.
- State: `backend/data/judge-live/`. Quota, each browser's ledger/audio and seller state
  persist here. Never delete it to bypass quota or reset an unfinished payment.
- Production static assets are built with same-origin `/buyer` and `/seller` URLs and
  an empty browser API token. Provider credentials stay server-side. No Vite dev server
  is published.
- The laptop must remain online and open during judging. The runner requests Windows
  to stay awake while it serves. This is a supervised demo, not an independently hosted
  production deployment.

## Bounds and isolation

Twelve admitted runs total, three per browser session, one active run globally. Failed
runs count. Counts persist across gateway restarts and new cookies cannot reset the
global limit. A run may use Codex/ElevenLabs quota and one paid Apify scrape; the run
limit is not a guaranteed dollar cap. Each scrape requests the existing $1.10 Actor
charge cap. At most 20 listings and six negotiation rounds are allowed.

Each browser gets an unpredictable HttpOnly, Secure, SameSite=Strict session cookie
and a separate buyer ledger, event stream, controls and speech directory. Spending
caps remain 10/8 by default. Cross-origin mutations are rejected. Public endpoints
are explicitly allowlisted; seller operations, documentation, private files and other
sessions' approvals/audio/history are not accessible. At most 32 sessions and two SSE
streams per session are admitted. Crash/restart remains in the recorded demonstration;
it is not a browser control for judges.

## Verification before publishing

- Eight gateway tests pass: cookie/auth boundary, cross-origin blocking, history/control/
  audio isolation, persistent session/global quotas, concurrency, request-size/round/
  listing limits, session capacity, and refusal of real payments/crash mode.
- Full pinned suite: 586 passed; one launcher test initially failed because the isolated
  checkout had no local `.venv` path. After linking the existing environment, that test
  and all eight gateway tests passed (nine targeted tests). No application failure was
  hidden by skipping a test.
- Separate production build and actual Edge browser: successful sample delivery, blocked
  con, refund, fourth-run rejection, empty history in a second session, no page errors.
  Evidence: `backend/data/judge-browser-check/browser-report.json`.
- Live public acceptance still required: HTTPS, fresh browser session, same-origin task
  creation, real streamed events, live Codex/Apify/ElevenLabs, audio playback, one release,
  and a second session unable to read the first. This acceptance consumes one of 12 runs.

## Later main-branch review (05:56)

The merged UI/general-answer revision `cc10f94` passed 679 backend tests, 63 frontend
tests and the production build in `backend/data/final-review`. Its browser passed
sample normal/con/refund runs, fourth-run rejection and separate-session history,
with zero page errors. Initial and completed desktop screenshots were inspected.
The subsequent funded-recovery revision `cb7a3be` passed all 66 affected tests.
Seven configured secret values were absent from all 223 tracked files at `cb7a3be`;
Gitleaks found no leaks in the three new commits since `d6b19a3`.

Evidence: `backend/data/final-review-check/{browser-report,source-review,gitleaks-delta}.json`.
Those results do not establish live general-answer/search acceptance. The prepared
public judge instance remains pinned to the already rehearsed rental workflow plus
the isolated gateway. The accepted video and presentation ZIP remain unchanged.

## Hosting checks and recovery

The existing Railway Masumi node passes health/authenticated Preprod-source checks.
This laptop has no Railway CLI login or deployment token configured. The payment node
is not the application host. Funding/registration/escrow remain unverified.

ngrok is configured but its agent cannot resolve its connection hostname on this
network, including with agent-specific DNS resolvers. Cloudflare account access and a
new named tunnel/DNS route work, but edge DNS resolution fails. The existing Trainbud
service configuration is unchanged. The user selected the Vercel recorded-page fallback.
Credentials remain in the user's Cloudflare directory and must not be committed.

After every current run finishes, the owning gateway can be stopped and restarted
using the same state directory. From a tested checkout's `backend/` directory:

```powershell
uv run --locked python scripts/judge.py --live --build --port 9200 --seller-port 9201 --max-runs 12 --session-runs 3 --state-dir C:/Users/zsadi/Desktop/Astra/backend/data/judge-live
```

On this laptop the ignored `backend/data/start_judge_instance.py --live` helper launches
the pinned source and passes the original private environment in memory. Runtime
process IDs are in `backend/data/judge-live/runtime.json`. Stop only those owned
processes after deals finish, never the separate development/recording services.
