# ziya — status
updated: 2026-10-08 23:25
doing: subscription-only migration complete; live Codex Max and fallback/guard checks passed
touching: Codex runtime, negotiation/config/tests/dependencies, env/docs/memory, dashboard provenance
blocked on: no I-path credential blocker; payment deployment continues in its separate session
next: rehearse with subscription Max; optional subscription Viktor remains I04
done today:
- scripts/up.py + scripts/act.py; all 4 acts verified live in SIMULATED mode
- 22:07 masumi mode Act 1+3 rehearsed over real HTTP vs fake node: 1 payment, 1 purchase, already_paid after crash
- 22:32 I01/I02 adapters ready, I03 honest readiness check, I05 TTS hardened, I06 ordered queue integrated; 129 Python + 7 JS tests and build pass; no live provider result claimed
- 22:35 verified all feature tips were already in main; deleted four local branches and remote feat/ziya-skeleton
- 22:46 legacy root folders archived under backend/data/legacy-workspace/20261008-224546; dependencies moved to frontend/node_modules; build and backend imports pass
- 22:51 generated node ADMIN_KEY/ENCRYPTION_KEY into local .env; .env.example documents node-side vars; Railway deploy pending Blockfrost key
- 22:55 Blockfrost Preprod project astra-masumi-preprod created; key in .env, tested 200
- 23:04 Railway project mellow-energy deployed; node URL https://masumi-payment-service-production-96e0.up.railway.app/api/v1; .env MASUMI_PAYMENT_URL updated; health pending
- 23:09 live Apify run ZNboU2b0EHUJgFaEQ saved 20 verified rentals; GET-only recovery passed; local cached mode selected
- 23:09 Brian/Callum speech passed; real HTTP Act 1 in Edge released SIMULATED escrow and played all 7 clips without overlap; 144 Python + 15 frontend tests/build pass
- 23:20 Railway build failed (seed restart loop, upstream Dockerfile bug); patched fork Zsadigzade/masumi-payment-service ce8cfdb5; Railway source switch to fork pending user (needs Railway GitHub App access)
- 23:25 permanent no-API constraint implemented; live checker + Act 1 Codex turns passed; 68 focused backend/15 frontend tests/build pass; five clips played, two text fallbacks
- 23:28 Railway source switched to fork, rebuild running; 23:30 encryption key confirmed not leaked
